import { useEffect, useRef } from "react";
import { useChatStore } from "../store/chatStore";
import { InputBar } from "./InputBar";
import { MessageBubble } from "./MessageBubble";

export function ChatWindow() {
  const messages = useChatStore((s) => s.messages);
  const initIfNeeded = useChatStore((s) => s.initIfNeeded);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    initIfNeeded();
  }, [initIfNeeded]);

  useEffect(() => {
    // The first two messages are the welcome text + initial asset picker — start at the
    // top of those rather than auto-scrolling straight to the bottom of a long picker.
    if (messages.length <= 2) return;
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const lastText = messages[messages.length - 1]?.text;
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [lastText]);

  return (
    <div className="flex h-full min-w-0 flex-1 flex-col">
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6 sm:px-8">
        <div className="mx-auto flex max-w-[760px] flex-col gap-3">
          {messages.map((m) => (
            <MessageBubble key={m.id} message={m} />
          ))}
        </div>
      </div>
      <InputBar />
    </div>
  );
}
