<script setup lang="ts">
import { ref, computed } from 'vue'

// === Upload Mode State ===
const file = ref<File | null>(null)
const uploadTaskId = ref<string | null>(null)
const uploadStatus = ref<string>('IDLE')
const uploadError = ref<string | null>(null)
let uploadPollInterval: NodeJS.Timeout | null = null

// === Generate Mode State ===
const prompt = ref<string>('')
const model = ref<string>('nano-banana')
const generateTaskId = ref<string | null>(null)
const generateStatus = ref<string>('IDLE')
const generateError = ref<string | null>(null)
let generatePollInterval: NodeJS.Timeout | null = null

// Model options
const modelOptions = [
  { label: 'Nano Banana (Fast)', value: 'nano-banana' },
  { label: 'Nano Banana Pro (Quality)', value: 'nano-banana-pro' }
]

// Tab items for UTabs - use 'slot' property for named slots
const tabItems = [
  { label: 'Upload Image', icon: 'i-heroicons-arrow-up-tray', slot: 'upload' },
  { label: 'Text to Sprite', icon: 'i-heroicons-sparkles', slot: 'generate' }
]

// === Upload Mode Functions ===
function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files && input.files[0]) {
    file.value = input.files[0]
    resetUploadState()
  }
}

function resetUploadState() {
  uploadTaskId.value = null
  uploadStatus.value = 'IDLE'
  uploadError.value = null
  if (uploadPollInterval) clearInterval(uploadPollInterval)
}

async function uploadFile() {
  if (!file.value) return

  uploadStatus.value = 'UPLOADING'
  const formData = new FormData()
  formData.append('file', file.value)

  try {
    const { data, error } = await useFetch('/api/process', {
      method: 'POST',
      body: formData
    })

    if (error.value) {
      throw new Error(error.value.message || 'Upload failed')
    }

    if (data.value && data.value.task_id) {
      uploadTaskId.value = data.value.task_id
      uploadStatus.value = 'PENDING'
      startUploadPolling()
    }
  } catch (e: any) {
    uploadStatus.value = 'FAILURE'
    uploadError.value = e.message
  }
}

function startUploadPolling() {
  uploadPollInterval = setInterval(async () => {
    if (!uploadTaskId.value) return

    try {
      const { data, error } = await useFetch(`/api/status/${uploadTaskId.value}`)

      if (error.value) throw new Error('Status check failed')

      const currentStatus = data.value?.status
      uploadStatus.value = currentStatus || 'UNKNOWN'

      if (currentStatus === 'SUCCESS') {
        clearInterval(uploadPollInterval!)
      } else if (currentStatus === 'FAILURE') {
        uploadError.value = data.value?.error || 'Unknown error'
        clearInterval(uploadPollInterval!)
      }
    } catch (e) {
      console.error(e)
    }
  }, 2000)
}

const uploadDownloadLink = computed(() => {
  if (!uploadTaskId.value) return ''
  return `/api/download/${uploadTaskId.value}`
})

// === Generate Mode Functions ===
function resetGenerateState() {
  generateTaskId.value = null
  generateStatus.value = 'IDLE'
  generateError.value = null
  if (generatePollInterval) clearInterval(generatePollInterval)
}

async function generateSprite() {
  if (!prompt.value.trim()) return

  generateStatus.value = 'UPLOADING'
  generateError.value = null

  try {
    const { data, error } = await useFetch('/api/generate', {
      method: 'POST',
      body: {
        prompt: prompt.value,
        model: model.value,
        auto_process: true
      }
    })

    if (error.value) {
      throw new Error(error.value.message || 'Generation failed')
    }

    if (data.value && data.value.task_id) {
      generateTaskId.value = data.value.task_id
      generateStatus.value = 'PENDING'
      startGeneratePolling()
    }
  } catch (e: any) {
    generateStatus.value = 'FAILURE'
    generateError.value = e.message
  }
}

function startGeneratePolling() {
  generatePollInterval = setInterval(async () => {
    if (!generateTaskId.value) return

    try {
      const { data, error } = await useFetch(`/api/status/${generateTaskId.value}`)

      if (error.value) throw new Error('Status check failed')

      const currentStatus = data.value?.status
      generateStatus.value = currentStatus || 'UNKNOWN'

      if (currentStatus === 'SUCCESS') {
        clearInterval(generatePollInterval!)
      } else if (currentStatus === 'FAILURE') {
        generateError.value = data.value?.error || 'Unknown error'
        clearInterval(generatePollInterval!)
      }
    } catch (e) {
      console.error(e)
    }
  }, 2000)
}

const generateDownloadLink = computed(() => {
  if (!generateTaskId.value) return ''
  return `/api/download/${generateTaskId.value}`
})

// Helper to map status to display text
function getStatusText(status: string): string {
  const statusMap: Record<string, string> = {
    'IDLE': 'Ready',
    'UPLOADING': 'Submitting...',
    'PENDING': 'Queued',
    'GENERATING': 'Generating Image...',
    'PROCESSING': 'Processing Sprites...',
    'PACKAGING': 'Packaging...',
    'SUCCESS': 'Complete',
    'FAILURE': 'Failed'
  }
  return statusMap[status] || status
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 font-sans">
    <UContainer class="py-12 max-w-2xl">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h1 class="text-2xl font-bold text-primary-500">Sprite Service</h1>
            <UBadge color="gray" variant="soft">Secure Gateway</UBadge>
          </div>
          <p class="text-gray-500 dark:text-gray-400 mt-2">
            Upload an image or generate from text to create game sprites.
          </p>
        </template>

        <!-- Tab Navigation with Named Slots -->
        <UTabs :items="tabItems" class="w-full">
          <!-- Upload Tab Content -->
          <template #upload>
            <div class="space-y-6 pt-4">
              <div class="flex flex-col gap-2">
                <label class="font-medium">Select Image (PNG/JPG)</label>
                <input
                  type="file"
                  accept="image/*"
                  @change="onFileChange"
                  class="block w-full text-sm text-gray-500
                    file:mr-4 file:py-2 file:px-4
                    file:rounded-full file:border-0
                    file:text-sm file:font-semibold
                    file:bg-primary-50 file:text-primary-700
                    hover:file:bg-primary-100
                    dark:file:bg-gray-800 dark:file:text-primary-400
                  "
                />
              </div>

              <UButton
                v-if="file"
                size="xl"
                block
                :loading="['UPLOADING', 'PENDING', 'PROCESSING'].includes(uploadStatus)"
                @click="uploadFile"
                :disabled="uploadStatus === 'SUCCESS'"
              >
                {{ uploadStatus === 'IDLE' ? 'Start Processing' : 'Processing...' }}
              </UButton>

              <!-- Upload Status Display -->
              <div v-if="uploadStatus !== 'IDLE'" class="p-4 rounded-lg bg-gray-100 dark:bg-gray-800 transition-all">
                <div class="flex items-center justify-between mb-2">
                  <span class="font-bold uppercase text-xs tracking-wider text-gray-500">Status</span>
                  <UBadge :color="uploadStatus === 'SUCCESS' ? 'green' : uploadStatus === 'FAILURE' ? 'red' : 'orange'">
                    {{ getStatusText(uploadStatus) }}
                  </UBadge>
                </div>

                <UProgress
                  v-if="['UPLOADING', 'PENDING', 'PROCESSING'].includes(uploadStatus)"
                  animation="carousel"
                  class="mt-2"
                />

                <div v-if="uploadStatus === 'FAILURE'" class="mt-4 text-red-500 text-sm">
                  Error: {{ uploadError }}
                </div>

                <div v-if="uploadStatus === 'SUCCESS'" class="mt-4 text-center">
                  <p class="mb-4 text-green-600 dark:text-green-400 font-medium">Processing Complete!</p>
                  <UButton
                    :to="uploadDownloadLink"
                    external
                    icon="i-heroicons-arrow-down-tray"
                    size="lg"
                    color="green"
                  >
                    Download Result (ZIP)
                  </UButton>
                </div>
              </div>
            </div>
          </template>

          <!-- Generate Tab Content -->
          <template #generate>
            <div class="space-y-6 pt-4">
              <!-- Prompt Input -->
              <div class="flex flex-col gap-2">
                <label class="font-medium">Describe your sprite</label>
                <UTextarea
                  v-model="prompt"
                  :rows="4"
                  placeholder="A fantasy knight sprite, pixel art style, transparent background, facing right..."
                  autoresize
                />
              </div>

              <!-- Model Selection -->
              <div class="flex flex-col gap-2">
                <label class="font-medium">Model</label>
                <USelectMenu
                  v-model="model"
                  :options="modelOptions"
                  value-attribute="value"
                  option-attribute="label"
                />
              </div>

              <!-- Generate Button -->
              <UButton
                size="xl"
                block
                icon="i-heroicons-sparkles"
                :loading="['UPLOADING', 'PENDING', 'GENERATING', 'PROCESSING', 'PACKAGING'].includes(generateStatus)"
                @click="generateSprite"
                :disabled="!prompt.trim() || generateStatus === 'SUCCESS'"
              >
                {{ generateStatus === 'IDLE' ? 'Generate Sprite' : 'Generating...' }}
              </UButton>

              <!-- Generate Status Display -->
              <div v-if="generateStatus !== 'IDLE'" class="p-4 rounded-lg bg-gray-100 dark:bg-gray-800 transition-all">
                <div class="flex items-center justify-between mb-2">
                  <span class="font-bold uppercase text-xs tracking-wider text-gray-500">Status</span>
                  <UBadge :color="generateStatus === 'SUCCESS' ? 'green' : generateStatus === 'FAILURE' ? 'red' : 'orange'">
                    {{ getStatusText(generateStatus) }}
                  </UBadge>
                </div>

                <UProgress
                  v-if="['UPLOADING', 'PENDING', 'GENERATING', 'PROCESSING', 'PACKAGING'].includes(generateStatus)"
                  animation="carousel"
                  class="mt-2"
                />

                <div v-if="generateStatus === 'FAILURE'" class="mt-4 text-red-500 text-sm">
                  Error: {{ generateError }}
                </div>

                <div v-if="generateStatus === 'SUCCESS'" class="mt-4 text-center">
                  <p class="mb-4 text-green-600 dark:text-green-400 font-medium">Generation Complete!</p>
                  <UButton
                    :to="generateDownloadLink"
                    external
                    icon="i-heroicons-arrow-down-tray"
                    size="lg"
                    color="green"
                  >
                    Download Sprites (ZIP)
                  </UButton>
                  <UButton
                    class="mt-2"
                    variant="soft"
                    block
                    @click="resetGenerateState"
                  >
                    Generate Another
                  </UButton>
                </div>
              </div>

              <!-- Info Box -->
              <UAlert
                icon="i-heroicons-information-circle"
                color="blue"
                variant="soft"
                title="How it works"
                description="Your text description will be used to generate an image using AI. The generated image will automatically go through background removal, sprite splitting, and multi-size output."
              />
            </div>
          </template>
        </UTabs>
      </UCard>
    </UContainer>
  </div>
</template>
