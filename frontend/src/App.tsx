import React, { type FC, useEffect } from "react";
import useApplicationStore from "./pages/store/ApplicationStore";
import { useAuth0 } from "@auth0/auth0-react";
import { Route, Routes } from "react-router-dom";
import { CallbackPage } from "./pages/CallbackPage";
import OnboardingPage from "./pages/onboarding/OnboardingPage";

const App: FC = function () {
  const { updateAuthentication } = useApplicationStore();
  const authContext = useAuth0();

  useEffect(() => {
    (async () => await updateAuthentication(authContext))();
  }, [authContext, updateAuthentication]);

  return (
    <Routes>
      <Route path="/" element={<OnboardingPage />} />
      <Route path="/callback" element={<CallbackPage />} />
    </Routes>
  );
};

export default App;
