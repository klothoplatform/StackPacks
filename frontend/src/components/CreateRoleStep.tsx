import { Button, List } from "flowbite-react";
import { env } from "../shared/environment.ts";
import { RiExternalLinkLine } from "react-icons/ri";
import React from "react";

// Update this if we want to include managed policies by default in addition to the custom policy we generate
const MANAGED_POLICIES = [].map(encodeURIComponent).join("&policies=");

export function CreateRoleStep(props: { externalId: string }) {
  return (
    <>
      <p>Create an IAM role in your AWS account using the link below.</p>

      <Button
        as={"a"}
        size={"xs"}
        target="_blank"
        rel="noopener noreferrer"
        href={`https://console.aws.amazon.com/iam/home#/roles/create?step=type&trustedEntityType=AWS_ACCOUNT&awsAccount=${env.awsAccountId}&isThirdParty=true&externalId=${props.externalId}${MANAGED_POLICIES ? "&policies=" + MANAGED_POLICIES : ""}`}
        color={"purple"}
        className={"size-fit items-center whitespace-nowrap"}
      >
        <span className={"flex items-center gap-1"}>
          Create role <RiExternalLinkLine />
        </span>
      </Button>
      <br />
      <p className={"pb-2"}>
        The following information will be prefilled for you.
      </p>
      <div className={"size-fit max-w-full px-2"}>
        <div
          className={"h-fit w-full rounded-lg bg-gray-100 p-4 dark:bg-gray-700"}
        >
          <List className={"text-gray-800 dark:text-gray-200"}>
            <List.Item>
              <span className={"font-medium"}>Trusted entity:</span>{" "}
              <code>AWS Account</code>
            </List.Item>
            <List.Item>
              <span className={"font-medium"}>Account ID:</span>{" "}
              <code>{env.awsAccountId}</code>
            </List.Item>
            <List.Item>
              <span className={"font-medium"}>External ID:</span>{" "}
              <code>{props.externalId}</code>
            </List.Item>
            <List.Item>
              <span className={"font-medium"}>Require MFA:</span>{" "}
              <code>unchecked</code>
            </List.Item>
          </List>
        </div>
      </div>
      <p className={"pt-2"}>
        Please do not make any modifications to these fields.
      </p>
    </>
  );
}
