import React, { type FC, useEffect } from "react";
import useApplicationStore from "./pages/store/ApplicationStore";
import { useAuth0 } from "@auth0/auth0-react";
import { Navigate, Route, Routes } from "react-router-dom";
import { CallbackPage } from "./pages/CallbackPage";
import OnboardingPage from "./pages/onboarding/OnboardingPage.tsx";

const App: FC = function () {
  const { updateAuthentication } = useApplicationStore();
  const authContext = useAuth0();

  useEffect(() => {
    (async () => await updateAuthentication(authContext))();
  }, [authContext, updateAuthentication]);

  return (
    <Routes>
      <Route path="/" element={<Navigate to={"/onboarding"} />} index />
      <Route path="/callback" element={<CallbackPage />} />
      <Route path="/onboarding" element={<OnboardingPage />} />
      <Route path="/onboarding/:step" element={<OnboardingPage />} />
    </Routes>
  );
};

export default App;
