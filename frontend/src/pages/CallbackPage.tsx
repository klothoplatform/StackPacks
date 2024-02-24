import React, { useEffect } from "react";
import { HeaderNavBar } from "../components/HeaderNavBar";
import { useNavigate } from "react-router-dom";
import useApplicationStore from "./store/ApplicationStore";

export const CallbackPage = () => {
  const navigate = useNavigate();

  const { isAuthenticated } = useApplicationStore();

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/");
    }
  }, [navigate, isAuthenticated]);
  return (
    <>
      <HeaderNavBar></HeaderNavBar>
    </>
  );
};
