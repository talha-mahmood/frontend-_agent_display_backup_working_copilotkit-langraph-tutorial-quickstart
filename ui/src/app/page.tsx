"use client";
import { useCopilotAction, useCopilotChat } from "@copilotkit/react-core";
import { CopilotPopup } from "@copilotkit/react-ui";
import { useState, useEffect } from "react";
import {
  Role,
  TextMessage,
  Message,
  AgentStateMessage,
  ActionExecutionMessage,
} from "@copilotkit/runtime-client-gql";

export default function YourApp() {
  // Track message type
  const [messageType, setMessageType] = useState<string | null>(null);

  // Access chat messages
  const { visibleMessages } = useCopilotChat();
  const messages = visibleMessages as Message[];

  // Extract message type from assistant messages
  useEffect(() => {
    if (!messages || messages.length === 0) return;
    // Find the last message with message_type in any supported format:
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i];
      console.log("Full Message is ", msg);

      // AgentStateMessage: state.message_type
      if (
        msg.type === "AgentStateMessage" &&
        (msg as AgentStateMessage).state &&
        typeof (msg as AgentStateMessage).state.message_type === "string"
      ) {
        setMessageType((msg as AgentStateMessage).state.message_type);
        console.log("The type of message is :", (msg as AgentStateMessage).state.message_type);
        break;
      }

      // ActionExecutionMessage: arguments.message_type
      if (
        msg.type === "ActionExecutionMessage" &&
        (msg as ActionExecutionMessage).arguments &&
        typeof (msg as ActionExecutionMessage).arguments.message_type === "string"
      ) {
        setMessageType((msg as ActionExecutionMessage).arguments.message_type);
        console.log("The type of message is :", (msg as ActionExecutionMessage).arguments.message_type);
        break;
      }

      // TextMessage: [message_type]: in content
      if (
        msg.type === "TextMessage" &&
        "role" in msg &&
        msg.role === Role.Assistant &&
        "content" in msg &&
        typeof msg.content === "string" &&
        msg.content.startsWith("[message_type]:")
      ) {
        // Only extract the first word after the colon as the message type
        const typeLine = msg.content.replace("[message_type]:", "").trim();
        const type = typeLine.split(/\s+/)[0]; // get only the first word
        setMessageType(type);
        console.log("The type of message is :", type);
        break;
      }
    }
  }, [messages]);

  useCopilotAction({
    name: "RequestAssistance",
    parameters: [
      {
        name: "request",
        type: "string",
      },
    ],
    renderAndWait: ({ args, status, handler }) => {
      const [response, setResponse] = useState("");
      return (
        <div className="p-4 bg-gray-100 rounded shadow-md">
          <p className="mb-2 text-gray-700">{args.request}</p>
          <div className="flex items-center space-x-2">
            <input
              type="text"
              className="flex-grow p-2 border border-gray-300 rounded"
              placeholder="Your response..."
              style={{ maxWidth: "calc(100% - 100px)" }}
              value={response}
              onChange={(e) => setResponse(e.target.value)}
            />
            {status === "executing" && (
              <button
                className="px-4 py-2 text-white bg-blue-500 rounded hover:bg-blue-600"
                onClick={() => handler(response)}
              >
                Submit
              </button>
            )}
          </div>
        </div>
      );
    },
  });

  return (
    <>
      {/* Display message type if available */}
      {messageType && (
        <div className="mb-4 p-2 bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 rounded">
          <strong>Agent called:</strong> {messageType}
        </div>
      )}
      <CopilotPopup
        instructions={
          "You are assisting the user as best as you can. Answer in the best way possible given the data you have."
        }
        defaultOpen={true}
        labels={{
          title: "Popup Assistant",
          initial: "Need any help?",
        }}
      />
    </>
  );
}
