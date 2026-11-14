// The "assistant" namespace's English texts: everything the assistant feature shows, grouped by area. Part of
// the assistant feature (i18n/). The source other languages translate (hi.ts); index.ts defines the namespace.
// Only the browser's own words are here: what the server sends (card and form texts, chip labels, the model's
// replies, error details) arrives already written.

/** The assistant feature's texts, in English. {{name}} marks a value filled in when the text is shown. */
const en = {
  panel: {
    title: "Assistant",
    newConversation: "New conversation",
    close: "Close assistant",
  },
  composer: {
    placeholder: "Ask or record an expense…",
    label: "Message",
    send: "Send",
    stop: "Stop",
    attach: "Attach a receipt (photo or PDF)",
    removeAttachment: "Remove {{name}}",
    attachmentTooLarge: "{{name}} is larger than {{max}} MB. Try a smaller photo or a shorter PDF.",
    attachmentType: "{{name}} can't be read as a receipt: attach a photo (JPEG, PNG or WEBP) or a PDF.",
  },
  transcript: {
    label: "Conversation",
    hint: "Ask about your spending, record an expense in plain words, or attach a receipt. Try:",
    thinking: "Thinking…",
    stopped: "Stopped.",
    sent: "Sent: {{values}}",
    attached: "Attached: {{name}}",
  },
  suggestions: {
    foodThisMonth: "How much did I spend on food this month?",
    addLunch: "Add 250 for lunch at Subway today, paid by UPI",
    biggestExpenses: "What were my 3 biggest expenses this month?",
  },
  chips: {
    notConfirmed: "The connection was lost before the result arrived. The pages have been reloaded.",
  },
  stream: {
    connectionLost: "The connection to the assistant was lost before the reply was finished.",
    notUnderstood: "The assistant sent something this app doesn't understand.",
  },
  cards: {
    choose: "Choose…",
    pickDate: "Pick a date",
    chartValue: "Amount",
  },
  unsupported: {
    multipleChoice: "Can't show a multiple-choice picker",
    timePicker: "Can't show a time picker",
    chartWithoutData: "Can't show a chart without data",
    chartKind: "Can't show this kind of chart",
    crashedCard: "Can't show this card (it couldn't be drawn)",
    tooLarge: "Can't show a card that's this large, or that contains itself",
    childNotId: "Can't show a child that isn't an id",
    tooDeep: "Can't show components nested this deep",
    unknownCatalog: "Can't show a component from a catalog this app doesn't know",
    unknownComponent: 'Can\'t show a "{{component}}" component',
    childList: "Can't show this kind of child list",
    textNotText: "Can't show a text that isn't text",
  },
}

export default en
