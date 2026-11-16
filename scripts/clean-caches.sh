#!/usr/bin/env bash
# Убирает кэши тестов/линта из worktree — включая созданные от root, без sudo.
#
# Зачем
# -----
# pytest, ruff, mypy и Vite пишут кэш рядом с кодом: `backend/.pytest_cache`,
# `backend/.ruff_cache`, `frontend/node_modules/.vite`. Если инструмент запускали
# в контейнере, куда смонтирован worktree (bind-mount сохраняет владельца файлов),
# на хосте каталоги принадлежат root. После мержа `git worktree remove` и
# `orca worktree rm` не могут их удалить (`Permission denied`), и уборка worktree
# требует sudo — а значит, ломает автоматическую уборку после мержа.
#
# Как
# ---
# Одноразовый контейнер монтирует корень репозитория и удаляет кэши от root:
# внутри контейнера процесс имеет те же права, что и процесс, создавший файлы,
# поэтому sudo на хосте не нужен. Удаляются только каталоги кэшей из списка
# `DEFAULT_PATHS`; код, тесты, node_modules целиком и `.git` не затрагиваются.
#
# Использование
# -------------
#   scripts/clean-caches.sh              # удалить кэши
#   scripts/clean-caches.sh --check      # проверить; exit 1, если кэши есть (docker не нужен)
#   scripts/clean-caches.sh --dry-run    # показать, что будет удалено
#   scripts/clean-caches.sh -- path ...  # кэши + дополнительные пути
#
# `CLEAN_CACHES_IMAGE` подменяет образ одноразового контейнера (по умолчанию
# `alpine:3`; нужна только утилита `rm`).

set -euo pipefail

IMAGE="${CLEAN_CACHES_IMAGE:-alpine:3}"

usage() {
  printf '%s\n' \
    "Использование: $(basename -- "$0") [--check | --dry-run] [-- путь ...]" \
    "" \
    "  (без флагов)  удалить кэши в worktree, включая root-owned, без sudo" \
    "  --check       не удалять, только проверить (exit 1, если кэши есть; docker не нужен)" \
    "  --dry-run     показать, что будет удалено" \
    "  -- путь ...   дополнительно обработать указанные пути (относительно корня репозитория)" \
    "" \
    "Переменная CLEAN_CACHES_IMAGE задаёт образ для одноразового контейнера."
}

# Список намеренно ограничен кэшами: скрипт не должен удалять код или node_modules.
DEFAULT_PATHS=(
  backend/.pytest_cache
  backend/.ruff_cache
  backend/.mypy_cache
  frontend/node_modules/.vite
  frontend/node_modules/.vite-temp
  e2e/test-results
  e2e/playwright-report
  .pytest_cache
  .ruff_cache
)

mode="clean"
extra_paths=()

while (($#)); do
  case "$1" in
    --check) mode="check" ;;
    --dry-run) mode="dry-run" ;;
    --clean) mode="clean" ;;
    -h | --help)
      usage
      exit 0
      ;;
    --)
      shift
      extra_paths+=("$@")
      break
      ;;
    -*)
      echo "Неизвестный флаг: $1" >&2
      usage >&2
      exit 2
      ;;
    *) extra_paths+=("$1") ;;
  esac
  shift
done

# Корень репозитория: скрипт работает из любого каталога и из worktree.
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if repo_root=$(git -C "$script_dir" rev-parse --show-toplevel 2>/dev/null); then
  :
else
  # Не git-репозиторий (например, распакованный архив) — корень выше scripts/.
  repo_root=$(dirname -- "$script_dir")
fi

targets=()
all_paths=("${DEFAULT_PATHS[@]}" ${extra_paths[@]+"${extra_paths[@]}"})
for path in "${all_paths[@]}"; do
  [[ -n "$path" ]] || continue
  case "$path" in
    "$repo_root"/*) path="${path#"$repo_root"/}" ;;
    /*)
      echo "Путь вне репозитория ($repo_root): $path" >&2
      exit 2
      ;;
  esac
  targets+=("${path#./}")
done

# Внутри контейнера /w — корень репозитория, пути уже относительные.
# shellcheck disable=SC2016  # скрипт намеренно в одинарных кавычках: его переменные раскрывает sh в контейнере
container_script='
action=$1
shift
found=0
for p in "$@"; do
  if [ -e "$p" ] || [ -L "$p" ]; then
    found=1
    owner=$(stat -c "%u:%g" "$p" 2>/dev/null || echo "?")
    case "$action" in
      dry-run) printf "будет удалён: %s (владелец %s)\n" "$p" "$owner" ;;
      *) rm -rf -- "$p" && printf "удалён: %s (владелец был %s)\n" "$p" "$owner" ;;
    esac
  fi
done
[ "$found" -eq 1 ] && exit 0
exit 3
'

run_in_container() {
  docker run --rm \
    -v "$repo_root:/w" \
    -w /w \
    --entrypoint sh \
    "$IMAGE" \
    -c "$container_script" sh "$mode" "${targets[@]}"
}

run_with_rm() {
  # Резерв, если docker недоступен: снимет только свои файлы, root-owned останется.
  local found=0
  for p in "${targets[@]}"; do
    if [[ -e "$repo_root/$p" || -L "$repo_root/$p" ]]; then
      found=1
      case "$mode" in
        dry-run) echo "будет удалён: $p" ;;
        *) rm -rf -- "${repo_root:?}/$p" && echo "удалён: $p" ;;
      esac
    fi
  done
  [[ "$found" -eq 1 ]]
}

echo "Корень репозитория: $repo_root"

# --check только смотрит на хост и не требует docker: так его можно звать из CI
# и из хуков, не поднимая контейнер.
if [[ "$mode" == "check" ]]; then
  remaining=()
  for p in "${targets[@]}"; do
    if [[ -e "$repo_root/$p" || -L "$repo_root/$p" ]]; then
      remaining+=("$p")
    fi
  done
  if ((${#remaining[@]})); then
    echo "Найдены кэши: ${remaining[*]}" >&2
    echo "Очистите их: scripts/clean-caches.sh" >&2
    exit 1
  fi
  echo "Кэшей нет: worktree чистый, уборка после мержа не заблокирована."
  exit 0
fi

if command -v docker >/dev/null 2>&1; then
  set +e
  run_in_container
  status=$?
  set -e
  if [[ "$status" -ne 0 && "$status" -ne 3 ]]; then
    echo "Одноразовый контейнер завершился с кодом $status." >&2
    echo "Проверьте, что доступен образ $IMAGE: docker pull $IMAGE" >&2
    exit "$status"
  fi
else
  echo "docker не найден — удаляю обычным rm (root-owned файлы так не удалятся)." >&2
  set +e
  run_with_rm
  set -e
fi

# Контроль на хосте: что не удалилось, то осталось root-owned или занято.
remaining=()
for p in "${targets[@]}"; do
  if [[ -e "$repo_root/$p" || -L "$repo_root/$p" ]]; then
    remaining+=("$p")
  fi
done

if [[ "$mode" == "dry-run" ]]; then
  echo "Прогон без изменений (--dry-run)."
  exit 0
fi

if ((${#remaining[@]})); then
  echo "Не удалось удалить: ${remaining[*]}" >&2
  echo "Права: ls -ld $repo_root/${remaining[0]}" >&2
  exit 1
fi

echo "Готово: кэшей в worktree нет, уборка worktree после мержа не заблокирована."