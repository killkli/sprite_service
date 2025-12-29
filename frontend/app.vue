<script setup lang="ts">
import { ref, computed } from 'vue'

const { t, locale, setLocale } = useI18n()

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

// === Image-to-Image Mode State ===
const useReferenceImage = ref<boolean>(false)
const referenceFile = ref<File | null>(null)
const referencePreviewUrl = ref<string | null>(null)

// === Advanced Parameters ===
const showAdvancedParams = ref<boolean>(false)
const temperature = ref<number>(1.0)
const distanceThreshold = ref<number>(80)
const sizeRatioThreshold = ref<number>(0.4)
const alphaThreshold = ref<number>(50)
const minAreaRatio = ref<number>(0.0005)
const maxAreaRatio = ref<number>(0.25)

// === Upload Mode Parameters ===
const uploadSplitMode = ref<'auto' | 'grid'>('auto')
const uploadDistanceThreshold = ref<number>(80)
const uploadSizeRatioThreshold = ref<number>(0.4)
const uploadAlphaThreshold = ref<number>(50)
const uploadMinAreaRatio = ref<number>(0.0005)
const uploadMaxAreaRatio = ref<number>(0.25)
const showUploadAdvancedParams = ref<boolean>(false)

// === Grid Parameters ===
const gridAutoDetect = ref<boolean>(true)
const gridRows = ref<number>(4)
const gridCols = ref<number>(4)
const gridPadding = ref<number>(2)
const gridLineThreshold = ref<number>(50)
const gridMinLineLengthRatio = ref<number>(0.3)

// Model options
const modelOptions = computed(() => [
  { label: t('generate.modelFast'), value: 'nano-banana' },
  { label: t('generate.modelQuality'), value: 'nano-banana-pro' }
])

// Language options
const languageOptions = [
  { label: '繁體中文', value: 'zh-TW' },
  { label: 'English', value: 'en' }
]

// Tab items for UTabs
const tabItems = computed(() => [
  { label: t('tabs.upload'), icon: 'i-heroicons-arrow-up-tray', slot: 'upload' },
  { label: t('tabs.generate'), icon: 'i-heroicons-sparkles', slot: 'generate' }
])

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

  let endpoint = '/api/process'

  if (uploadSplitMode.value === 'grid') {
    // Grid split mode
    endpoint = '/api/process/grid'
    formData.append('auto_detect', gridAutoDetect.value.toString())
    if (!gridAutoDetect.value) {
      formData.append('rows', gridRows.value.toString())
      formData.append('cols', gridCols.value.toString())
    }
    formData.append('padding', gridPadding.value.toString())
    formData.append('line_threshold', gridLineThreshold.value.toString())
    formData.append('min_line_length_ratio', gridMinLineLengthRatio.value.toString())
  } else {
    // Auto detect mode (background removal)
    formData.append('distance_threshold', uploadDistanceThreshold.value.toString())
    formData.append('size_ratio_threshold', uploadSizeRatioThreshold.value.toString())
    formData.append('alpha_threshold', uploadAlphaThreshold.value.toString())
    formData.append('min_area_ratio', uploadMinAreaRatio.value.toString())
    formData.append('max_area_ratio', uploadMaxAreaRatio.value.toString())
  }

  try {
    const { data, error } = await useFetch(endpoint, {
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

function onReferenceFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files && input.files[0]) {
    referenceFile.value = input.files[0]
    if (referencePreviewUrl.value) {
      URL.revokeObjectURL(referencePreviewUrl.value)
    }
    referencePreviewUrl.value = URL.createObjectURL(input.files[0])
  }
}

function clearReferenceImage() {
  referenceFile.value = null
  if (referencePreviewUrl.value) {
    URL.revokeObjectURL(referencePreviewUrl.value)
    referencePreviewUrl.value = null
  }
}

async function generateSprite() {
  if (!prompt.value.trim()) return

  if (useReferenceImage.value && !referenceFile.value) {
    generateError.value = t('error.uploadReference')
    return
  }

  generateStatus.value = 'UPLOADING'
  generateError.value = null

  try {
    let response: any

    if (useReferenceImage.value && referenceFile.value) {
      const formData = new FormData()
      formData.append('prompt', prompt.value)
      formData.append('model', model.value)
      formData.append('auto_process', 'true')
      formData.append('reference_image', referenceFile.value)
      formData.append('temperature', temperature.value.toString())
      formData.append('distance_threshold', distanceThreshold.value.toString())
      formData.append('size_ratio_threshold', sizeRatioThreshold.value.toString())
      formData.append('alpha_threshold', alphaThreshold.value.toString())
      formData.append('min_area_ratio', minAreaRatio.value.toString())
      formData.append('max_area_ratio', maxAreaRatio.value.toString())

      const { data, error } = await useFetch('/api/generate/with-reference', {
        method: 'POST',
        body: formData
      })

      if (error.value) {
        throw new Error(error.value.message || 'Generation failed')
      }
      response = data.value
    } else {
      const { data, error } = await useFetch('/api/generate', {
        method: 'POST',
        body: {
          prompt: prompt.value,
          model: model.value,
          auto_process: true,
          temperature: temperature.value,
          distance_threshold: distanceThreshold.value,
          size_ratio_threshold: sizeRatioThreshold.value,
          alpha_threshold: alphaThreshold.value,
          min_area_ratio: minAreaRatio.value,
          max_area_ratio: maxAreaRatio.value
        }
      })

      if (error.value) {
        throw new Error(error.value.message || 'Generation failed')
      }
      response = data.value
    }

    if (response && response.task_id) {
      generateTaskId.value = response.task_id
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

function getStatusText(status: string): string {
  const statusMap: Record<string, string> = {
    'IDLE': t('status.ready'),
    'UPLOADING': t('status.submitting'),
    'PENDING': t('status.queued'),
    'GENERATING': t('status.generating'),
    'PROCESSING': t('status.processing'),
    'PACKAGING': t('status.packaging'),
    'SUCCESS': t('status.complete'),
    'FAILURE': t('status.failed')
  }
  return statusMap[status] || status
}

function changeLanguage(lang: string) {
  setLocale(lang)
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 font-sans">
    <UContainer class="py-12 max-w-2xl">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h1 class="text-2xl font-bold text-primary-500">{{ t('app.title') }}</h1>
            <div class="flex items-center gap-2">
              <USelectMenu
                :model-value="locale"
                :options="languageOptions"
                value-attribute="value"
                option-attribute="label"
                size="sm"
                class="w-32"
                @update:model-value="changeLanguage"
              />
              <UBadge color="gray" variant="soft">{{ t('app.secureGateway') }}</UBadge>
            </div>
          </div>
          <p class="text-gray-500 dark:text-gray-400 mt-2">
            {{ t('app.subtitle') }}
          </p>
        </template>

        <UTabs :items="tabItems" class="w-full">
          <!-- Upload Tab Content -->
          <template #upload>
            <div class="space-y-6 pt-4">
              <div class="flex flex-col gap-2">
                <label class="font-medium">{{ t('upload.selectImage') }}</label>
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

              <!-- Split Mode Selection -->
              <div class="flex flex-col gap-2">
                <label class="font-medium">{{ t('upload.splitMode') }}</label>
                <div class="grid grid-cols-2 gap-4">
                  <button
                    @click="uploadSplitMode = 'auto'"
                    :class="[
                      'p-4 rounded-lg border-2 text-left transition-all',
                      uploadSplitMode === 'auto'
                        ? 'border-primary-500 bg-primary-50 dark:bg-primary-950'
                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                    ]"
                  >
                    <div class="flex items-center gap-2 mb-1">
                      <UIcon name="i-heroicons-sparkles" class="text-lg" />
                      <span class="font-medium">{{ t('upload.splitModeAuto') }}</span>
                    </div>
                    <p class="text-xs text-gray-500">{{ t('upload.splitModeAutoDesc') }}</p>
                  </button>
                  <button
                    @click="uploadSplitMode = 'grid'"
                    :class="[
                      'p-4 rounded-lg border-2 text-left transition-all',
                      uploadSplitMode === 'grid'
                        ? 'border-primary-500 bg-primary-50 dark:bg-primary-950'
                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                    ]"
                  >
                    <div class="flex items-center gap-2 mb-1">
                      <UIcon name="i-heroicons-table-cells" class="text-lg" />
                      <span class="font-medium">{{ t('upload.splitModeGrid') }}</span>
                    </div>
                    <p class="text-xs text-gray-500">{{ t('upload.splitModeGridDesc') }}</p>
                  </button>
                </div>
              </div>

              <!-- Advanced Parameters Toggle -->
              <div class="border rounded-lg p-4 bg-gray-50 dark:bg-gray-900">
                <button
                  @click="showUploadAdvancedParams = !showUploadAdvancedParams"
                  class="flex items-center justify-between w-full text-left font-medium"
                >
                  <span>{{ t('params.title') }}</span>
                  <UIcon :name="showUploadAdvancedParams ? 'i-heroicons-chevron-up' : 'i-heroicons-chevron-down'" />
                </button>

                <div v-if="showUploadAdvancedParams" class="mt-4 space-y-4">
                  <!-- Auto Detect Mode Parameters -->
                  <template v-if="uploadSplitMode === 'auto'">
                    <h4 class="text-sm font-semibold text-gray-600 dark:text-gray-400">{{ t('params.processing') }}</h4>

                    <div>
                      <div class="flex justify-between text-sm mb-1">
                        <label>{{ t('params.distanceThreshold.label') }}: {{ uploadDistanceThreshold }}</label>
                      </div>
                      <URange v-model="uploadDistanceThreshold" :min="10" :max="500" :step="10" />
                      <p class="text-xs text-gray-500 mt-1">{{ t('params.distanceThreshold.description') }}</p>
                    </div>

                    <div>
                      <div class="flex justify-between text-sm mb-1">
                        <label>{{ t('params.sizeRatioThreshold.label') }}: {{ uploadSizeRatioThreshold.toFixed(2) }}</label>
                      </div>
                      <URange v-model="uploadSizeRatioThreshold" :min="0.1" :max="1.0" :step="0.05" />
                      <p class="text-xs text-gray-500 mt-1">{{ t('params.sizeRatioThreshold.description') }}</p>
                    </div>

                    <div>
                      <div class="flex justify-between text-sm mb-1">
                        <label>{{ t('params.alphaThreshold.label') }}: {{ uploadAlphaThreshold }}</label>
                      </div>
                      <URange v-model="uploadAlphaThreshold" :min="1" :max="254" :step="1" />
                      <p class="text-xs text-gray-500 mt-1">{{ t('params.alphaThreshold.description') }}</p>
                    </div>

                    <div>
                      <div class="flex justify-between text-sm mb-1">
                        <label>{{ t('params.minAreaRatio.label') }}: {{ uploadMinAreaRatio.toFixed(4) }}</label>
                      </div>
                      <URange v-model="uploadMinAreaRatio" :min="0.0001" :max="0.1" :step="0.0001" />
                      <p class="text-xs text-gray-500 mt-1">{{ t('params.minAreaRatio.description') }}</p>
                    </div>

                    <div>
                      <div class="flex justify-between text-sm mb-1">
                        <label>{{ t('params.maxAreaRatio.label') }}: {{ uploadMaxAreaRatio.toFixed(2) }}</label>
                      </div>
                      <URange v-model="uploadMaxAreaRatio" :min="0.05" :max="0.9" :step="0.05" />
                      <p class="text-xs text-gray-500 mt-1">{{ t('params.maxAreaRatio.description') }}</p>
                    </div>
                  </template>

                  <!-- Grid Mode Parameters -->
                  <template v-else>
                    <h4 class="text-sm font-semibold text-gray-600 dark:text-gray-400">{{ t('params.gridParams') }}</h4>

                    <div>
                      <div class="flex items-center justify-between mb-2">
                        <label class="text-sm">{{ t('params.autoDetect.label') }}</label>
                        <UToggle v-model="gridAutoDetect" />
                      </div>
                      <p class="text-xs text-gray-500">{{ t('params.autoDetect.description') }}</p>
                    </div>

                    <div v-if="!gridAutoDetect" class="grid grid-cols-2 gap-4">
                      <div>
                        <div class="flex justify-between text-sm mb-1">
                          <label>{{ t('params.gridRows.label') }}: {{ gridRows }}</label>
                        </div>
                        <URange v-model="gridRows" :min="1" :max="20" :step="1" />
                        <p class="text-xs text-gray-500 mt-1">{{ t('params.gridRows.description') }}</p>
                      </div>

                      <div>
                        <div class="flex justify-between text-sm mb-1">
                          <label>{{ t('params.gridCols.label') }}: {{ gridCols }}</label>
                        </div>
                        <URange v-model="gridCols" :min="1" :max="20" :step="1" />
                        <p class="text-xs text-gray-500 mt-1">{{ t('params.gridCols.description') }}</p>
                      </div>
                    </div>

                    <div>
                      <div class="flex justify-between text-sm mb-1">
                        <label>{{ t('params.gridPadding.label') }}: {{ gridPadding }}</label>
                      </div>
                      <URange v-model="gridPadding" :min="0" :max="20" :step="1" />
                      <p class="text-xs text-gray-500 mt-1">{{ t('params.gridPadding.description') }}</p>
                    </div>

                    <div v-if="gridAutoDetect">
                      <div class="flex justify-between text-sm mb-1">
                        <label>{{ t('params.lineThreshold.label') }}: {{ gridLineThreshold }}</label>
                      </div>
                      <URange v-model="gridLineThreshold" :min="10" :max="200" :step="10" />
                      <p class="text-xs text-gray-500 mt-1">{{ t('params.lineThreshold.description') }}</p>
                    </div>

                    <div v-if="gridAutoDetect">
                      <div class="flex justify-between text-sm mb-1">
                        <label>{{ t('params.minLineLengthRatio.label') }}: {{ gridMinLineLengthRatio.toFixed(2) }}</label>
                      </div>
                      <URange v-model="gridMinLineLengthRatio" :min="0.1" :max="1.0" :step="0.05" />
                      <p class="text-xs text-gray-500 mt-1">{{ t('params.minLineLengthRatio.description') }}</p>
                    </div>
                  </template>
                </div>
              </div>

              <UButton
                v-if="file"
                size="xl"
                block
                :loading="['UPLOADING', 'PENDING', 'PROCESSING'].includes(uploadStatus)"
                @click="uploadFile"
                :disabled="uploadStatus === 'SUCCESS'"
              >
                {{ uploadStatus === 'IDLE' ? t('upload.startProcessing') : t('upload.processing') }}
              </UButton>

              <!-- Upload Status Display -->
              <div v-if="uploadStatus !== 'IDLE'" class="p-4 rounded-lg bg-gray-100 dark:bg-gray-800 transition-all">
                <div class="flex items-center justify-between mb-2">
                  <span class="font-bold uppercase text-xs tracking-wider text-gray-500">{{ t('status.label') }}</span>
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
                  {{ t('error.prefix') }} {{ uploadError }}
                </div>

                <div v-if="uploadStatus === 'SUCCESS'" class="mt-4 text-center">
                  <p class="mb-4 text-green-600 dark:text-green-400 font-medium">{{ t('result.complete') }}</p>
                  <UButton
                    :to="uploadDownloadLink"
                    external
                    icon="i-heroicons-arrow-down-tray"
                    size="lg"
                    color="green"
                  >
                    {{ t('result.downloadZip') }}
                  </UButton>
                </div>
              </div>
            </div>
          </template>

          <!-- Generate Tab Content -->
          <template #generate>
            <div class="space-y-6 pt-4">
              <!-- Mode Toggle -->
              <div class="flex flex-col gap-2">
                <label class="font-medium">{{ t('generate.mode') }}</label>
                <div class="flex items-center gap-4">
                  <UToggle v-model="useReferenceImage" />
                  <span class="text-sm text-gray-600 dark:text-gray-400">
                    {{ useReferenceImage ? t('generate.imageToImage') : t('generate.textToImage') }}
                  </span>
                </div>
              </div>

              <!-- Reference Image Upload -->
              <div v-if="useReferenceImage" class="flex flex-col gap-2">
                <label class="font-medium">{{ t('generate.referenceImage') }}</label>
                <div class="border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-lg p-4">
                  <div v-if="referencePreviewUrl" class="relative">
                    <img
                      :src="referencePreviewUrl"
                      alt="Reference"
                      class="max-h-48 mx-auto rounded-lg"
                    />
                    <UButton
                      icon="i-heroicons-x-mark"
                      color="red"
                      variant="soft"
                      size="xs"
                      class="absolute top-2 right-2"
                      @click="clearReferenceImage"
                    />
                  </div>
                  <div v-else class="text-center">
                    <input
                      type="file"
                      accept="image/*"
                      @change="onReferenceFileChange"
                      class="block w-full text-sm text-gray-500
                        file:mr-4 file:py-2 file:px-4
                        file:rounded-full file:border-0
                        file:text-sm file:font-semibold
                        file:bg-primary-50 file:text-primary-700
                        hover:file:bg-primary-100
                        dark:file:bg-gray-800 dark:file:text-primary-400
                      "
                    />
                    <p class="mt-2 text-xs text-gray-400">{{ t('generate.uploadReference') }}</p>
                  </div>
                </div>
              </div>

              <!-- Prompt Input -->
              <div class="flex flex-col gap-2">
                <label class="font-medium">
                  {{ useReferenceImage ? t('generate.editInstruction') : t('generate.describeSprite') }}
                </label>
                <UTextarea
                  v-model="prompt"
                  :rows="4"
                  :placeholder="useReferenceImage ? t('generate.editPlaceholder') : t('generate.promptPlaceholder')"
                  autoresize
                />
              </div>

              <!-- Model Selection -->
              <div class="flex flex-col gap-2">
                <label class="font-medium">{{ t('generate.model') }}</label>
                <USelectMenu
                  v-model="model"
                  :options="modelOptions"
                  value-attribute="value"
                  option-attribute="label"
                />
              </div>

              <!-- Advanced Parameters -->
              <div class="border rounded-lg p-4 bg-gray-50 dark:bg-gray-900">
                <button
                  @click="showAdvancedParams = !showAdvancedParams"
                  class="flex items-center justify-between w-full text-left font-medium"
                >
                  <span>{{ t('params.title') }}</span>
                  <UIcon :name="showAdvancedParams ? 'i-heroicons-chevron-up' : 'i-heroicons-chevron-down'" />
                </button>

                <div v-if="showAdvancedParams" class="mt-4 space-y-4">
                  <!-- Generation Parameters -->
                  <h4 class="text-sm font-semibold text-gray-600 dark:text-gray-400">{{ t('params.generation') }}</h4>

                  <div>
                    <div class="flex justify-between text-sm mb-1">
                      <label>{{ t('params.temperature.label') }}: {{ temperature.toFixed(1) }}</label>
                    </div>
                    <URange v-model="temperature" :min="0" :max="2" :step="0.1" />
                    <p class="text-xs text-gray-500 mt-1">{{ t('params.temperature.description') }}</p>
                  </div>

                  <!-- Processing Parameters -->
                  <h4 class="text-sm font-semibold text-gray-600 dark:text-gray-400 mt-6">{{ t('params.processing') }}</h4>

                  <div>
                    <div class="flex justify-between text-sm mb-1">
                      <label>{{ t('params.distanceThreshold.label') }}: {{ distanceThreshold }}</label>
                    </div>
                    <URange v-model="distanceThreshold" :min="10" :max="500" :step="10" />
                    <p class="text-xs text-gray-500 mt-1">{{ t('params.distanceThreshold.description') }}</p>
                  </div>

                  <div>
                    <div class="flex justify-between text-sm mb-1">
                      <label>{{ t('params.sizeRatioThreshold.label') }}: {{ sizeRatioThreshold.toFixed(2) }}</label>
                    </div>
                    <URange v-model="sizeRatioThreshold" :min="0.1" :max="1.0" :step="0.05" />
                    <p class="text-xs text-gray-500 mt-1">{{ t('params.sizeRatioThreshold.description') }}</p>
                  </div>

                  <div>
                    <div class="flex justify-between text-sm mb-1">
                      <label>{{ t('params.alphaThreshold.label') }}: {{ alphaThreshold }}</label>
                    </div>
                    <URange v-model="alphaThreshold" :min="1" :max="254" :step="1" />
                    <p class="text-xs text-gray-500 mt-1">{{ t('params.alphaThreshold.description') }}</p>
                  </div>

                  <div>
                    <div class="flex justify-between text-sm mb-1">
                      <label>{{ t('params.minAreaRatio.label') }}: {{ minAreaRatio.toFixed(4) }}</label>
                    </div>
                    <URange v-model="minAreaRatio" :min="0.0001" :max="0.1" :step="0.0001" />
                    <p class="text-xs text-gray-500 mt-1">{{ t('params.minAreaRatio.description') }}</p>
                  </div>

                  <div>
                    <div class="flex justify-between text-sm mb-1">
                      <label>{{ t('params.maxAreaRatio.label') }}: {{ maxAreaRatio.toFixed(2) }}</label>
                    </div>
                    <URange v-model="maxAreaRatio" :min="0.05" :max="0.9" :step="0.05" />
                    <p class="text-xs text-gray-500 mt-1">{{ t('params.maxAreaRatio.description') }}</p>
                  </div>
                </div>
              </div>

              <!-- Generate Button -->
              <UButton
                size="xl"
                block
                icon="i-heroicons-sparkles"
                :loading="['UPLOADING', 'PENDING', 'GENERATING', 'PROCESSING', 'PACKAGING'].includes(generateStatus)"
                @click="generateSprite"
                :disabled="!prompt.trim() || generateStatus === 'SUCCESS' || (useReferenceImage && !referenceFile)"
              >
                {{ generateStatus === 'IDLE' ? (useReferenceImage ? t('generate.generateFromRef') : t('generate.generateSprite')) : t('generate.generating') }}
              </UButton>

              <!-- Generate Status Display -->
              <div v-if="generateStatus !== 'IDLE'" class="p-4 rounded-lg bg-gray-100 dark:bg-gray-800 transition-all">
                <div class="flex items-center justify-between mb-2">
                  <span class="font-bold uppercase text-xs tracking-wider text-gray-500">{{ t('status.label') }}</span>
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
                  {{ t('error.prefix') }} {{ generateError }}
                </div>

                <div v-if="generateStatus === 'SUCCESS'" class="mt-4 text-center">
                  <p class="mb-4 text-green-600 dark:text-green-400 font-medium">{{ t('result.complete') }}</p>
                  <UButton
                    :to="generateDownloadLink"
                    external
                    icon="i-heroicons-arrow-down-tray"
                    size="lg"
                    color="green"
                  >
                    {{ t('result.downloadSprites') }}
                  </UButton>
                  <UButton
                    class="mt-2"
                    variant="soft"
                    block
                    @click="resetGenerateState"
                  >
                    {{ t('result.generateAnother') }}
                  </UButton>
                </div>
              </div>

              <!-- Info Box -->
              <UAlert
                icon="i-heroicons-information-circle"
                color="blue"
                variant="soft"
                :title="t('info.title')"
                :description="useReferenceImage ? t('info.imageToImage') : t('info.textToImage')"
              />
            </div>
          </template>
        </UTabs>
      </UCard>
    </UContainer>
  </div>
</template>
