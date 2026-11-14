// Server-Sent Events framing for the assistant's stream: split the text into events, take each event's `data:`
// lines, and read a stream as those data strings as they arrive. Knows nothing about AG-UI; agent-stream.ts
// parses what comes out. Also defines the "connection lost" message, since this is where a break shows up.

import { isAbort } from "@/shared/lib/errors"

/** What a run says when the connection breaks, or the stream ends, before the reply is finished. */
export const CONNECTION_LOST = "The connection to the assistant was lost before the reply was finished."

const SSE_EVENT_END = "\n\n"
const SSE_LINE_END = "\n"
const SSE_DATA = "data:"

/**
 * Splits buffered stream text into complete events (each ends with a blank line) and the unfinished tail. A
 * piece of the stream can end mid-event, so `rest` is kept and the next piece is added to it.
 */
export function splitEvents(buffer: string): { events: string[]; rest: string } {
  const events = buffer.split(SSE_EVENT_END)
  const rest = events.pop() ?? ""
  return { events, rest }
}

/** One SSE event block's `data:` lines, joined. Comments (FastAPI's ": ping" keep-alives) have none: "". */
export function dataOf(block: string): string {
  return block
    .split(SSE_LINE_END)
    .filter((line) => line.startsWith(SSE_DATA))
    .map((line) => line.slice(SSE_DATA.length).trimStart())
    .join(SSE_LINE_END)
}

// One read. Stopped on purpose (Stop, or the page closed) stays an AbortError; a network drop mid-reply
// becomes CONNECTION_LOST.
async function read(reader: ReadableStreamDefaultReader<string>): Promise<ReadableStreamReadResult<string>> {
  try {
    return await reader.read()
  } catch (error) {
    if (isAbort(error)) throw error
    throw new Error(CONNECTION_LOST)
  }
}

/**
 * Reads `stream` piece by piece as it arrives and yields each event's data, skipping events without any. Ends
 * when the stream does. Throws an AbortError if the request was stopped, or an Error(CONNECTION_LOST) if the
 * network dropped. However it ends (including the caller breaking out early), the reader is cancelled, which
 * closes the connection.
 */
export async function* sseData(stream: ReadableStream<string>): AsyncGenerator<string, void, undefined> {
  const reader = stream.getReader()
  let buffer = ""
  try {
    for (;;) {
      const { value, done } = await read(reader)
      if (done) return
      const { events, rest } = splitEvents(buffer + value)
      buffer = rest
      for (const block of events) {
        const data = dataOf(block)
        if (data) yield data
      }
    }
  } finally {
    // Nothing to do if the stream already ended; a failed cancel has nothing left to clean up.
    reader.cancel().catch(() => {})
  }
}
