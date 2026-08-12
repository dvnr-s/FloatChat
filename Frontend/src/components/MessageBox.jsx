import React, { useState, useRef, useEffect } from "react";
import axios from "axios";

const MessageBox = () => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const messagesEndRef = useRef(null);

    const sendMessage = async () => {
        if (!input.trim()) return;

        const newMessage = { sender: "user", text: input };
        setMessages((prev) => [...prev, newMessage]);
        setInput("");

        try {
            // Send message to backend
            const res = await axios.post("http://127.0.0.1:8001/chat", {
  user_input: input,
});

            console.log("Reached")
            const replytext = res.data.response;

// Find index of "Final Answer"
const marker = "Final Answer";
const index = replytext.indexOf(marker);

let finalans;
if (index !== -1) {
  // Extract everything after "Final Answer"
  finalans = replytext
    .substring(index + marker.length)  // get text after marker
    .replace(/^[:\-]?\s*/, "");        // remove leading ":" or "-" and spaces
} else {
  finalans = replytext; // fallback if no "Final Answer" found
}

console.log("Extracted final answer:", replytext);

const botMessage = { sender: "bot", text: finalans };

            setMessages((prev) => [...prev, botMessage]);
        } catch (err) {
            console.error("Error sending message:", err);
            const errorMessage = { sender: "bot", text: "⚠️ Error: Unable to reach server." };
            setMessages((prev) => [...prev, errorMessage]);
        }
    };
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    return (
        <div className="w-full max-w-7xl bg-gradient-to-r from-gray-800/90 to-gray-700/90 backdrop-blur-md border border-gray-600 rounded-3xl p-6 shadow-2xl flex flex-col">
            <div className="overflow-y-auto h-120 border-b border-gray-600 mb-6 p-4 bg-gradient-to-b from-gray-900/50 to-gray-800/50 rounded-xl">
                <div className="flex-1 overflow-y-auto space-y-3 mb-4 flex flex-col">
                    {messages.map((msg, i) => (
                        <div
                            key={i}
                            className={`py-3 px-4 rounded-xl inline-block max-w-[75%] break-words ${msg.sender === "user"
                                ? "bg-gradient-to-r from-blue-800 to-emerald-800 text-white ml-auto text-right"
                                : "bg-gradient-to-r from-emerald-800 to-indigo-800 text-white"
                                }`}
                        >
                            {msg.text}
                        </div>
                    ))}
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
                    className="cursor-pointer w-30 px-6 py-3 rounded-2xl bg-gradient-to-r from-sky-700 to-emerald-600 
             text-white font-semibold transition-all duration-200 
             hover:shadow-[0_0_20px_rgba(56,189,248,0.7)] 
             hover:scale-100"
                >
                    Send
                </button>

            </div>
            <div ref={messagesEndRef} />
        </div>
    );
};

export default MessageBox;
