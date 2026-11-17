import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "../api/client";

interface ApiDataState<T> {
  data: T | null;
  error: string | null;
  isLoading: boolean;
}

interface ApiDataResult<T> extends ApiDataState<T> {
  /** Повторить запрос, не меняя фильтры. */
  reload: () => void;
}

/**
 * Загрузка данных API с понятным текстом ошибки и повтором запроса.
 *
 * `loader` должен быть стабильным (`useCallback` с реальными зависимостями):
 * смена его идентичности перезапускает запрос. Ответы устаревших запросов
 * отбрасываются по счётчику, поэтому быстрый ввод в поиск не перезаписывает
 * свежие данные старыми.
 */
export function useApiData<T>(
  loader: () => Promise<T>,
  fallbackError = "Не удалось загрузить данные.",
): ApiDataResult<T> {
  const [state, setState] = useState<ApiDataState<T>>({
    data: null,
    error: null,
    isLoading: true,
  });
  const requestSeq = useRef(0);

  const run = useCallback(() => {
    const seq = requestSeq.current + 1;
    requestSeq.current = seq;
    setState((previous) => ({ ...previous, isLoading: true, error: null }));

    loader()
      .then((data) => {
        if (requestSeq.current === seq) {
          setState({ data, error: null, isLoading: false });
        }
      })
      .catch((cause: unknown) => {
        if (requestSeq.current === seq) {
          setState((previous) => ({
            data: previous.data,
            error: cause instanceof ApiError ? cause.message : fallbackError,
            isLoading: false,
          }));
        }
      });
  }, [loader, fallbackError]);

  useEffect(() => {
    run();
    // Сбрасываем счётчик при размонтировании: поздние ответы не трогают state.
    return () => {
      requestSeq.current += 1;
    };
  }, [run]);

  return { ...state, reload: run };
}
