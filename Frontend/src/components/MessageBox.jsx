import React, { useState, useRef, useEffect } from "react";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// The agent still narrates its ReAct scaffolding into the reply. Keep only the
// answer: everything after the last "Final Answer", minus any stray step lines.
const extractAnswer = (raw) => {
    if (!raw) return "";
    const marker = /final\s*(answer|findings)\s*[:\-]?/gi;
    let text = raw;
    let lastMatch = null;
    for (const m of raw.matchAll(marker)) lastMatch = m;
    if (lastMatch) text = raw.slice(lastMatch.index + lastMatch[0].length);
    return text
        .split("\n")
        .filter((line) => !/^\s*(thought|action|observation|action input)\s*:/i.test(line))
        .join("\n")
        .trim();
};

// Tailwind v4 here has no typography plugin, so map each element explicitly.
const markdownComponents = {
    h1: (p) => <h1 className="text-lg font-bold text-sky-200 mt-3 mb-2" {...p} />,
    h2: (p) => <h2 className="text-base font-bold text-sky-200 mt-3 mb-2" {...p} />,
    h3: (p) => <h3 className="text-sm font-bold uppercase tracking-wide text-sky-300/90 mt-3 mb-1" {...p} />,
    p: (p) => <p className="leading-relaxed mb-2 last:mb-0" {...p} />,
    strong: (p) => <strong className="font-semibold text-white" {...p} />,
    ul: (p) => <ul className="list-disc ml-5 space-y-1 mb-2" {...p} />,
    ol: (p) => <ol className="list-decimal ml-5 space-y-1 mb-2" {...p} />,
    code: (p) => <code className="bg-black/30 rounded px-1.5 py-0.5 text-sky-200 text-[0.85em]" {...p} />,
    a: (p) => <a className="text-sky-300 underline underline-offset-2" target="_blank" rel="noreferrer" {...p} />,
    // Tables are the point of remark-gfm — let wide ones scroll instead of
    // bursting the chat bubble.
    table: (p) => (
        <div className="overflow-x-auto my-3 rounded-lg border border-white/15">
            <table className="w-full text-sm border-collapse" {...p} />
        </div>
    ),
    thead: (p) => <thead className="bg-white/10" {...p} />,
    th: (p) => <th className="text-left font-semibold px-3 py-2 border-b border-white/15 whitespace-nowrap" {...p} />,
    td: (p) => <td className="px-3 py-2 border-b border-white/5 align-top" {...p} />,
    tr: (p) => <tr className="hover:bg-white/5 transition-colors" {...p} />,
};

const MessageBox = () => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef(null);

    const sendMessage = async () => {
        if (!input.trim() || loading) return;

        const question = input;
        setMessages((prev) => [...prev, { sender: "user", text: question }]);
        setInput("");
        setLoading(true);

        try {
            const res = await axios.post("http://127.0.0.1:8001/chat", {
                user_input: question,
            });
            setMessages((prev) => [
                ...prev,
                { sender: "bot", text: extractAnswer(res.data.response) },
            ]);
        } catch (err) {
            console.error("Error sending message:", err);
            setMessages((prev) => [
                ...prev,
                { sender: "bot", text: "⚠️ Error: Unable to reach server." },
            ]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, loading]);

    return (
        <div className="w-full max-w-7xl bg-gradient-to-r from-gray-800/90 to-gray-700/90 backdrop-blur-md border border-gray-600 rounded-3xl p-6 shadow-2xl flex flex-col">
            <div className="overflow-y-auto h-120 border-b border-gray-600 mb-6 p-4 bg-gradient-to-b from-gray-900/50 to-gray-800/50 rounded-xl">
                <div className="flex-1 overflow-y-auto space-y-3 mb-4 flex flex-col">
                    {messages.map((msg, i) =>
                        msg.sender === "user" ? (
                            <div
                                key={i}
                                className="py-3 px-4 rounded-xl inline-block max-w-[75%] break-words bg-gradient-to-r from-blue-800 to-emerald-800 text-white ml-auto text-right"
                            >
                                {msg.text}
                            </div>
                        ) : (
                            // Wider than the user bubble so data tables have room.
                            <div
                                key={i}
                                className="py-3 px-4 rounded-xl max-w-[92%] break-words bg-gradient-to-r from-emerald-800 to-indigo-800 text-white"
                            >
                                <ReactMarkdown
                                    remarkPlugins={[remarkGfm]}
                                    components={markdownComponents}
                                >
                                    {msg.text}
                                </ReactMarkdown>
                            </div>
                        )
                    )}

                    {loading && (
                        <div className="py-3 px-4 rounded-xl bg-gradient-to-r from-emerald-800 to-indigo-800 text-white/80 inline-flex items-center gap-2 self-start">
                            <span className="w-2 h-2 rounded-full bg-sky-300 animate-bounce [animation-delay:-0.3s]" />
                            <span className="w-2 h-2 rounded-full bg-sky-300 animate-bounce [animation-delay:-0.15s]" />
                            <span className="w-2 h-2 rounded-full bg-sky-300 animate-bounce" />
                            <span className="ml-2 text-sm">Querying Argo floats…</span>
                        </div>
                    )}
                </div>
            </div>

            {/* Input */}
            <div className="flex gap-2">
                <input
                    className="flex-1 p-3 rounded-2xl bg-gray-700/80 border border-gray-600 text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:shadow-xl focus:shadow-sky-400/80 focus:ring-sky-500 transition duration-400 "
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                    placeholder="Type a message..."
                />
                <button
                    onClick={sendMessage}
                    disabled={loading}
                    className="cursor-pointer w-30 px-6 py-3 rounded-2xl bg-gradient-to-r from-sky-700 to-emerald-600
             text-white font-semibold transition-all duration-200
             hover:shadow-[0_0_20px_rgba(56,189,248,0.7)]
             hover:scale-100 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {loading ? "…" : "Send"}
                </button>

            </div>
            <div ref={messagesEndRef} />
        </div>
    );
};

export default MessageBox;
