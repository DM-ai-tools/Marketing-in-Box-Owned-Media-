/** Client for the sign-in gate (`app/routers/auth.py`). Email and password only.
 *
 * Separate from `pipelineApi.ts` and `usageApi.ts` for the same reason those are separate from each
 * other: nothing here participates in a run, and the module that can create accounts should not
 * also be able to advance a stage.
 *
 * **There is no token in this file, deliberately.** The session lives in an httpOnly cookie the
 * backend sets, so it is unreachable from JavaScript — including from any script that manages to
 * execute inside the model-authored HTML this app renders (see `HtmlPreview`). Every call below
 * therefore passes `credentials: "include"` and carries no `Authorization` header; "am I signed
 * in?" is a question only the server can answer, which is what `fetchMe` is for.
 */

export interface AuthUser {
  id: string;
  email: string;
  full_name: string | null;
  /** True once a reset link sent to the address has been redeemed — the only proof of ownership
   * this system can obtain. A fresh signup starts false. */
  email_verified: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface AuthConfig {
  /** The API's own minimum, so the form can never accept a password the API will reject. */
  password_min_length: number;
}

export interface AccountState {
  exists: boolean;
  /** Present only when the account exists; used to greet a returning user by name. */
  full_name?: string | null;
}

/** An API rejection carrying the backend's own user-facing message.
 *
 * Every `AuthError` message in `app/services/auth.py` is written to be read by a person, so this
 * is rendered verbatim rather than translated into a second set of strings here — two copies of
 * "incorrect email or password" is two things to keep in step, and the frontend copy would be the
 * one that goes stale. `status` is kept for the few places that branch on it.
 */
export class AuthApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "AuthApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, {
      ...init,
      // The whole session mechanism. Without this the browser sends no cookie and every
      // authenticated call answers 401 while looking, from the client's side, like a signed-out
      // user — a failure mode that is very hard to read backwards from the symptom.
      credentials: "include",
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    // A network-level failure, not a rejected credential: the backend is down or unreachable.
    // Named as such so the form does not tell someone their password is wrong when it never
    // reached the server.
    throw new AuthApiError("Cannot reach the server. Check that the backend is running.", 0);
  }

  if (res.status === 204) return undefined as T;

  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const detail =
      (body && typeof body.detail === "string" && body.detail) ||
      `Request failed (${res.status}).`;
    throw new AuthApiError(detail, res.status);
  }
  return body as T;
}

export function fetchAuthConfig(): Promise<AuthConfig> {
  return request<AuthConfig>("/api/auth/config");
}

/** Whether an address already has an account — the pivot of the email-first form.
 *
 * The one call that decides whether a visitor is shown "enter your password" or "create your
 * account", so they never have to pick the right tab before they have told us who they are.
 */
export function checkEmail(email: string): Promise<AccountState> {
  return request<AccountState>("/api/auth/check-email", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export function signup(email: string, password: string, fullName?: string): Promise<AuthUser> {
  return request<AuthUser>("/api/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email, password, full_name: fullName || null }),
  });
}

export function login(email: string, password: string): Promise<AuthUser> {
  return request<AuthUser>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

/** The signed-in user, or `null` on 401.
 *
 * A 401 here is the ordinary signed-out answer, not a failure, so it is mapped to `null` instead
 * of thrown — the boot path should not have to treat "nobody is logged in" as an exception. Any
 * other status still throws, because "the backend is unreachable" and "you are not signed in" call
 * for very different screens.
 */
export async function fetchMe(): Promise<AuthUser | null> {
  try {
    return await request<AuthUser>("/api/auth/me");
  } catch (err) {
    if (err instanceof AuthApiError && err.status === 401) return null;
    throw err;
  }
}

export function logout(): Promise<{ message: string }> {
  return request<{ message: string }>("/api/auth/logout", { method: "POST" });
}

/** Ask for a reset link. Always resolves with the same message whether or not the account exists —
 * see the route's docstring; the UI shows it verbatim rather than implying an account was found. */
export function forgotPassword(email: string): Promise<{ message: string }> {
  return request<{ message: string }>("/api/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

/** Redeem a reset link. Resolves to the now-signed-in user: proving control of the mailbox is
 * enough to be let in, so the flow ends in the app rather than back at the sign-in form. */
export function resetPassword(token: string, password: string): Promise<AuthUser> {
  return request<AuthUser>("/api/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({ token, password }),
  });
}
