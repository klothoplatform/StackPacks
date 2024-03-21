import type { StateCreator } from "zustand";
import type { Auth0ContextInterface, User } from "@auth0/auth0-react";
import type { ErrorStore } from "./ErrorStore";
import { env } from "../../shared/environment";
import { analytics } from "../../shared/analytics.ts";

const logoutUrl = env.auth0.logoutUrl;

export interface AuthStoreState {
  auth0?: Auth0ContextInterface;
  currentIdToken: { idToken: string; expiresAt: number };
  isAuthenticated: boolean;
  redirectedPostLogin: boolean;
  user?: User;
  isLoggingIn: boolean;
  _refresh_result?: Promise<{ idToken: string; expiresAt: number }>;
}

export interface AuthStoreBase extends AuthStoreState {
  getIdToken: () => Promise<string>;
  logout: () => void;
  loginWithRedirect: (appState: { [key: string]: any }) => Promise<void>;
  updateAuthentication: (context: Auth0ContextInterface) => Promise<void>;
  resetAuthState: () => void;
}

const initialState: () => AuthStoreState = () => ({
  auth0: undefined,
  currentIdToken: { idToken: "", expiresAt: 0 },
  isAuthenticated: false,
  redirectedPostLogin: false,
  user: undefined,
  isLoggingIn: false,
});

export type AuthStore = AuthStoreBase & ErrorStore;

export const authStore: StateCreator<AuthStore, [], [], AuthStoreBase> = (
  set: (state: object, replace?: boolean, id?: string) => any,
  get,
) => ({
  ...initialState(),
  getIdToken: async () => {
    let { idToken, expiresAt } = get().currentIdToken;
    const fiveMinutesInSeconds = 60 * 5;
    const fiveMinutesAgo = Date.now() / 1000 - fiveMinutesInSeconds;
    const isExpired = expiresAt - fiveMinutesAgo < fiveMinutesInSeconds;
    if (idToken && !isExpired) {
      return idToken;
    }
    const auth0 = get().auth0;
    if (!auth0 || (!auth0.isAuthenticated && !auth0.isLoading)) {
      return "";
    }
    const refresh = async () => {
      console.log("refreshing token");
      const auth0 = get().auth0;
      if (!auth0) {
        console.log("no auth0");
        return { idToken: "", expiresAt: 0 };
      }
      const refreshId = crypto.randomUUID().toString();

      set({ _refresh_id: refreshId }, false, "getIdToken/refresh");
      await auth0.getAccessTokenSilently({
        cacheMode: "off",
      });
      const claims = await auth0.getIdTokenClaims();
      if (!claims) {
        console.log("unauthenticated user");
        return { idToken: "", expiresAt: 0 };
      }
      console.log("refreshed token");
      return {
        idToken: claims.__raw,
        expiresAt: claims.exp ?? 0,
      };
    };
    if (get()._refresh_result) {
      return (await get()._refresh_result).idToken;
    }

    try {
      const result = refresh();
      set({ _refresh_result: result }, false, "getIdToken:refreshing");
      const { idToken, expiresAt } = await result;
      set(
        { currentIdToken: { idToken, expiresAt } },
        false,
        "getIdToken:refreshed",
      );
    } catch (e) {
      throw new Error("User session has expired. Please log in again.");
    }
    return idToken;
  },
  logout: () => {
    console.log(logoutUrl, "logouturl");
    get().auth0?.logout({
      logoutParams: { returnTo: logoutUrl },
    });
  },
  loginWithRedirect: async (appState: { [key: string]: any }) => {
    const auth0 = get().auth0;
    if (!auth0) {
      return;
    }

    if (!get().isAuthenticated && !auth0.isLoading) {
      set({ isLoggingIn: true }, false, "loginWithRedirect/isLoggingIn");
      await auth0.loginWithRedirect({
        appState: {
          ...appState,
        },
      });
    }
  },

  updateAuthentication: async (context: Auth0ContextInterface) => {
    const { getIdTokenClaims, isAuthenticated, user } = context;
    const claims = await getIdTokenClaims();
    if (!claims) {
      set(
        {
          currentIdToken: { idToken: "", expiresAt: 0 },
          user: undefined,
          isAuthenticated: false,
          auth0: context,
          isLoggingIn: context.isLoading,
        },
        false,
        "updateAuthentication/unauthenticated",
      );
      return;
    }

    const oldUser = get().user;
    if (user?.sub && oldUser?.sub !== user?.sub) {
      (async () =>
        analytics.identify(user?.sub, {
          name: user?.name,
          email: user?.email,
          environment: env.environment,
        }))();
      if (user?.email) {
        (window as any).sessionRewind?.identifyUser({
          userId: user.email,
          userName: user.name,
        });
      }
    }
    set(
      {
        currentIdToken: {
          idToken: claims.__raw,
          expiresAt: claims.exp ?? 0,
        },
        user,
        isAuthenticated,
        auth0: context,
        isLoggingIn: !isAuthenticated,
      },
      false,
      "updateAuthentication/authenticated",
    );
  },
  resetAuthState: () => set(initialState(), false, "resetAuthState"),
});
