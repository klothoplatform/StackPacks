import React, { type FC } from "react";
import {
  isRouteErrorResponse,
  useNavigate,
  useRouteError,
} from "react-router-dom";
import { PiSmileyXEyes } from "react-icons/pi";
import { Button } from "flowbite-react";
import { FaHome } from "react-icons/fa";

const messages = new Map([
  [404, "This page doesn't exist!"],
  [401, "You aren't authorized to see this!"],
  [503, "Looks like our API is down!"],
  [418, "🫖"],
]);

export const FallbackPage: FC = () => {
  const navigate = useNavigate();
  const error = useRouteError();
  let message = "Something went wrong!";

  if (isRouteErrorResponse(error)) {
    message = messages.get(error.status) || message;
  }
  console.log(message);

  return (
    <div
      className={
        "absolute left-0 top-0 flex h-screen w-screen items-center justify-center overflow-hidden bg-gray-200 dark:bg-gray-900"
      }
    >
      <div
        role="alert"
        className="flex size-fit flex-col items-center justify-center dark:text-white"
      >
        <div className="flex size-fit flex-col items-center justify-center gap-2">
          <p className={"text-md mb-1 font-medium"}>{message}</p>
          <PiSmileyXEyes size={"3rem"} />
          <Button
            className="sized-fit mt-4 whitespace-nowrap"
            color={"light"}
            onClick={() => navigate("/", { replace: true })}
          >
            <FaHome className={"mr-2"} /> Take me home
          </Button>
        </div>
      </div>
    </div>
  );
};

export default FallbackPage;
