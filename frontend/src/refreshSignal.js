import { ref } from 'vue'

/** Bumped after a practice attempt is saved so history / profile can reload. */
export const attemptRevision = ref(0)

export function notifyAttemptSaved() {
  attemptRevision.value += 1
}
