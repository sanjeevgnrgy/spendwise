// The "auth" namespace's English texts: the sign-in page, the session check in front of the pages, and the user
// menu. Part of the auth feature (i18n/). The source other languages translate (hi.ts); index.ts defines the
// namespace and bundles this file, because the session check and the menu are part of the app's frame.

/** The auth feature's texts, in English. {{name}} marks a value filled in when the text is shown. */
const en = {
  signIn: {
    title: "Sign in to {{app}}",
    description: "Choose how you'd like to sign in.",
    continueWith: "Continue with {{provider}}",
    signIn: "Sign in",
    loadingOptions: "Loading the ways to sign in…",
    optionsFailed: "Couldn't load the ways to sign in",
  },
  // Why the last sign-in didn't complete: the server's ?error= codes (the contract's AUTH.failures), and a text for
  // a code this app doesn't know.
  failures: {
    cancelled: "Sign-in was cancelled.",
    expired: "That sign-in took too long or was already used. Please try again.",
    rejected: "The sign-in couldn't be verified. Please try again.",
    notAllowed: "This account isn't allowed to use {{app}}. Ask the owner for access.",
    unavailable: "Sign-in isn't available right now. Try again in a moment.",
    unknown: "Sign-in didn't complete. Please try again.",
  },
  session: {
    checking: "Checking your sign-in…",
    checkFailed: "Couldn't check whether you're signed in",
  },
  userMenu: {
    label: "Account menu for {{name}}",
    you: "Your account",
    signedInAs: "Signed in as",
    signOut: "Sign out",
  },
}

export default en
