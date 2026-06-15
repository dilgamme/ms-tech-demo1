const IMAGE_ACTION_PATTERN =
  /\b(create|generate|draw|make|design|illustrate)\b.{0,100}\b(image|picture|photo|logo|poster|diagram|illustration)\b/i

const IMAGE_ARTIFACT_PATTERN =
  /\b(image|picture|photo|logo|poster|diagram|illustration)\b\s+(of|showing|depicting|with|for)\b/i

export const isImageGenerationPrompt = (prompt = '') => (
  IMAGE_ACTION_PATTERN.test(prompt)
  || IMAGE_ARTIFACT_PATTERN.test(prompt)
)
