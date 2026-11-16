import { useSyncExternalStore } from "react";

import { getCurrentUserId, subscribeCurrentUser } from "../api/currentUser";

/** Текущий пользователь из общего store (его же читает api-клиент для `X-User-Id`). */
export function useCurrentUserId(): number | null {
  return useSyncExternalStore(subscribeCurrentUser, getCurrentUserId, getCurrentUserId);
}
