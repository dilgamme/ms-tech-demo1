import api from './api'

const TARGET_SAMPLE_RATE = 24000

export const createVoiceLiveSocket = () => {
  const baseUrl = new URL(api.defaults.baseURL)
  baseUrl.protocol = baseUrl.protocol === 'https:' ? 'wss:' : 'ws:'
  baseUrl.pathname = '/api/voice/live'
  baseUrl.search = ''
  return new WebSocket(baseUrl.toString())
}

export const createPcmRecorder = async (onAudioChunk) => {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
  })
  const audioContext = new AudioContext()
  const source = audioContext.createMediaStreamSource(stream)
  const processor = audioContext.createScriptProcessor(4096, 1, 1)

  processor.onaudioprocess = (event) => {
    const input = event.inputBuffer.getChannelData(0)
    const pcm16 = floatToPcm16(downsample(input, audioContext.sampleRate, TARGET_SAMPLE_RATE))
    onAudioChunk(arrayBufferToBase64(pcm16.buffer))
  }

  source.connect(processor)
  processor.connect(audioContext.destination)

  return {
    stop: async () => {
      processor.disconnect()
      source.disconnect()
      stream.getTracks().forEach((track) => track.stop())
      await audioContext.close()
    },
  }
}

export const createPcmPlayer = () => {
  const audioContext = new AudioContext({ sampleRate: TARGET_SAMPLE_RATE })
  let nextStartTime = audioContext.currentTime
  let closed = false
  const sources = new Set()

  return {
    play: async (base64Audio) => {
      if (closed) {
        return
      }
      if (audioContext.state === 'suspended') {
        await audioContext.resume()
      }

      const pcm = base64ToInt16Array(base64Audio)
      const audioBuffer = audioContext.createBuffer(1, pcm.length, TARGET_SAMPLE_RATE)
      const channel = audioBuffer.getChannelData(0)
      for (let index = 0; index < pcm.length; index += 1) {
        channel[index] = pcm[index] / 32768
      }

      const source = audioContext.createBufferSource()
      source.buffer = audioBuffer
      source.connect(audioContext.destination)
      sources.add(source)
      source.onended = () => {
        sources.delete(source)
      }

      const startAt = Math.max(nextStartTime, audioContext.currentTime)
      source.start(startAt)
      nextStartTime = startAt + audioBuffer.duration
    },
    interrupt: () => {
      sources.forEach((source) => {
        try {
          source.stop()
        } catch {
          // The source may already have ended.
        }
      })
      sources.clear()
      nextStartTime = audioContext.currentTime
    },
    waitUntilDone: async () => {
      const remainingMs = Math.max(0, (nextStartTime - audioContext.currentTime) * 1000)
      if (remainingMs > 0) {
        await new Promise((resolve) => {
          window.setTimeout(resolve, remainingMs + 150)
        })
      }
    },
    close: async () => {
      if (!closed) {
        closed = true
        sources.forEach((source) => {
          try {
            source.stop()
          } catch {
            // The source may already have ended.
          }
        })
        sources.clear()
        await audioContext.close()
      }
    },
  }
}

const downsample = (input, inputSampleRate, outputSampleRate) => {
  if (inputSampleRate === outputSampleRate) {
    return input
  }

  const ratio = inputSampleRate / outputSampleRate
  const outputLength = Math.floor(input.length / ratio)
  const output = new Float32Array(outputLength)

  for (let outputIndex = 0; outputIndex < outputLength; outputIndex += 1) {
    const inputIndex = Math.floor(outputIndex * ratio)
    output[outputIndex] = input[inputIndex]
  }

  return output
}

const floatToPcm16 = (float32Array) => {
  const pcm16 = new Int16Array(float32Array.length)
  for (let index = 0; index < float32Array.length; index += 1) {
    const sample = Math.max(-1, Math.min(1, float32Array[index]))
    pcm16[index] = sample < 0 ? sample * 0x8000 : sample * 0x7fff
  }
  return pcm16
}

const arrayBufferToBase64 = (buffer) => {
  let binary = ''
  const bytes = new Uint8Array(buffer)
  for (let index = 0; index < bytes.byteLength; index += 1) {
    binary += String.fromCharCode(bytes[index])
  }
  return btoa(binary)
}

const base64ToInt16Array = (base64) => {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index)
  }
  return new Int16Array(bytes.buffer)
}
