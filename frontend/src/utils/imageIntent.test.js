import assert from 'node:assert/strict'
import test from 'node:test'

import { isImageGenerationPrompt } from './imageIntent.js'

test('recognizes explicit image generation requests', () => {
  assert.equal(isImageGenerationPrompt('Create an image of a futuristic datacenter'), true)
  assert.equal(isImageGenerationPrompt('Design a logo for MS Tech Demo'), true)
  assert.equal(isImageGenerationPrompt('A diagram showing the request flow'), true)
})

test('does not treat general design and creation tasks as image requests', () => {
  assert.equal(
    isImageGenerationPrompt(
      'Design an architecture for a multi-region Kubernetes API and compare active-active with active-passive.',
    ),
    false,
  )
  assert.equal(isImageGenerationPrompt('Create a migration plan for this workload'), false)
  assert.equal(isImageGenerationPrompt('Make this email more professional'), false)
})
