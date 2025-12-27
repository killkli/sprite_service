<script setup lang="ts">
import { ref } from 'vue'

const file = ref<File | null>(null)
const taskId = ref<string | null>(null)
const status = ref<string>('IDLE') // IDLE, UPLOADING, PENDING, PROCESSING, SUCCESS, FAILURE
const errorMsg = ref<string | null>(null)
const downloadUrl = ref<string | null>(null)
let pollInterval: NodeJS.Timeout | null = null

// Handle file selection
function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files && input.files[0]) {
    file.value = input.files[0]
    resetState()
  }
}

function resetState() {
  taskId.value = null
  status.value = 'IDLE'
  errorMsg.value = null
  downloadUrl.value = null
  if (pollInterval) clearInterval(pollInterval)
}

// Upload file
async function uploadFile() {
  if (!file.value) return

  status.value = 'UPLOADING'
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
      taskId.value = data.value.task_id
      status.value = 'PENDING'
      startPolling()
    }
  } catch (e: any) {
    status.value = 'FAILURE'
    errorMsg.value = e.message
  }
}

// Poll status
function startPolling() {
  pollInterval = setInterval(async () => {
    if (!taskId.value) return

    try {
      const { data, error } = await useFetch(`/api/status/${taskId.value}`)
      
      if (error.value) {
        throw new Error('Status check failed')
      }

      const currentStatus = data.value?.status
      status.value = currentStatus || 'UNKNOWN'

      if (currentStatus === 'SUCCESS') {
        downloadUrl.value = data.value?.download_url // This comes from Python as /download/...
        clearInterval(pollInterval!)
      } else if (currentStatus === 'FAILURE') {
        errorMsg.value = data.value?.error || 'Unknown error'
        clearInterval(pollInterval!)
      }
    } catch (e) {
      console.error(e)
      // Don't stop polling immediately on network hiccup, but maybe handle count
    }
  }, 2000)
}

// Get correct download link (proxied)
const proxyDownloadLink = computed(() => {
  if (!taskId.value) return ''
  return `/api/download/${taskId.value}`
})
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
            Upload an image to remove background, split sprites, and resize automatically.
          </p>
        </template>

        <div class="space-y-6">
          <!-- File Input -->
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

          <!-- Action Button -->
          <UButton 
            v-if="file"
            size="xl" 
            block 
            :loading="status === 'UPLOADING' || status === 'PENDING' || status === 'PROCESSING'"
            @click="uploadFile"
            :disabled="status === 'SUCCESS'"
          >
            {{ status === 'IDLE' ? 'Start Processing' : 'Processing...' }}
          </UButton>

          <!-- Status Display -->
          <div v-if="status !== 'IDLE'" class="p-4 rounded-lg bg-gray-100 dark:bg-gray-800 transition-all">
            <div class="flex items-center justify-between mb-2">
              <span class="font-bold uppercase text-xs tracking-wider text-gray-500">Status</span>
              <UBadge :color="status === 'SUCCESS' ? 'green' : status === 'FAILURE' ? 'red' : 'orange'">
                {{ status }}
              </UBadge>
            </div>
            
            <UProgress 
              v-if="['UPLOADING', 'PENDING', 'PROCESSING'].includes(status)" 
              animation="carousel" 
              class="mt-2" 
            />

            <!-- Error Message -->
            <div v-if="status === 'FAILURE'" class="mt-4 text-red-500 text-sm">
              Error: {{ errorMsg }}
            </div>

            <!-- Success Result -->
            <div v-if="status === 'SUCCESS'" class="mt-4 text-center">
              <p class="mb-4 text-green-600 dark:text-green-400 font-medium">Processing Complete!</p>
              <UButton 
                :to="proxyDownloadLink" 
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
      </UCard>
    </UContainer>
  </div>
</template>