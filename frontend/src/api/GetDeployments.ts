import type { AxiosResponse } from "axios";
import axios from "axios";
import { ApiError } from "../shared/errors";

export async function getDeployments(idToken: string) {
  let response: AxiosResponse;
  try {
    response = await axios.get(`/api/deployments`, {
      headers: idToken && { Authorization: `Bearer ${idToken}` },
    });
  } catch (error) {
    throw new ApiError({
      status: error.response.status,
      statusText: error.response.statusText,
      message: error.response.data.message,
      cause: error,
      errorId: "GetDeploymentsError",
    });
  }

  return response.data;
}
