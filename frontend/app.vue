<script setup lang="ts">
import { ref, computed } from 'vue'

const { t, locale, setLocale } = useI18n()

// === Tab State ===
const activeTab = ref<'upload' | 'generate'>('upload')

// === Upload Mode State ===
const file = ref<File | null>(null)
const filePreviewUrl = ref<string | null>(null)
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

// === Custom Output Sizes ===
interface CustomSize {
  name: string
  width: number
  height: number
}

const useCustomSizes = ref<boolean>(false)
const customSizes = ref<CustomSize[]>([
  { name: 'large', width: 256, height: 256 },
  { name: 'medium', width: 128, height: 128 },
  { name: 'small', width: 64, height: 64 }
])

function addCustomSize() {
  customSizes.value.push({ name: '', width: 64, height: 64 })
}

function removeCustomSize(index: number) {
  if (customSizes.value.length > 1) {
    customSizes.value.splice(index, 1)
  }
}

function getOutputSizesJson(): string | null {
  if (!useCustomSizes.value) return null
  const sizes: Record<string, number[]> = {}
  for (const size of customSizes.value) {
    if (size.name.trim()) {
      sizes[size.name.trim()] = [size.width, size.height]
    }
  }
  return Object.keys(sizes).length > 0 ? JSON.stringify(sizes) : null
}

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

// === Upload Mode Functions ===
function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files && input.files[0]) {
    file.value = input.files[0]
    if (filePreviewUrl.value) {
      URL.revokeObjectURL(filePreviewUrl.value)
    }
    filePreviewUrl.value = URL.createObjectURL(input.files[0])
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

  // Add custom output sizes if enabled
  const outputSizesJson = getOutputSizesJson()
  if (outputSizesJson) {
    formData.append('output_sizes_json', outputSizesJson)
  }

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

    // Get custom output sizes if enabled
    const outputSizesJson = getOutputSizesJson()
    const outputSizes = outputSizesJson ? JSON.parse(outputSizesJson) : undefined

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
      if (outputSizesJson) {
        formData.append('output_sizes_json', outputSizesJson)
      }

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
          max_area_ratio: maxAreaRatio.value,
          output_sizes: outputSizes
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

// Drag and drop handling
const isDragging = ref(false)

function onDragOver(e: DragEvent) {
  e.preventDefault()
  isDragging.value = true
}

function onDragLeave() {
  isDragging.value = false
}

function onDrop(e: DragEvent) {
  e.preventDefault()
  isDragging.value = false
  const files = e.dataTransfer?.files
  if (files && files[0] && files[0].type.startsWith('image/')) {
    file.value = files[0]
    if (filePreviewUrl.value) {
      URL.revokeObjectURL(filePreviewUrl.value)
    }
    filePreviewUrl.value = URL.createObjectURL(files[0])
    resetUploadState()
  }
}
</script>

<template>
  <div class="app-container">
    <!-- CRT Scanline Overlay -->
    <div class="crt-overlay"></div>
    <!-- Pixel Grid Background -->
    <div class="pixel-grid-bg"></div>

    <div class="main-wrapper">
      <!-- Console Panel -->
      <div class="console-panel corner-brackets">
        <!-- Header -->
        <header class="panel-header">
          <div>
            <h1 class="panel-title animate-flicker">{{ t('app.title') }}</h1>
            <p class="panel-subtitle">{{ t('app.subtitle') }}</p>
          </div>
          <div class="header-controls">
            <!-- Language Selector -->
            <div class="lang-selector">
              <select
                :value="locale"
                @change="changeLanguage(($event.target as HTMLSelectElement).value)"
                class="lang-btn"
              >
                <option v-for="lang in languageOptions" :key="lang.value" :value="lang.value">
                  {{ lang.label }}
                </option>
              </select>
            </div>
            <!-- Status Badge -->
            <div class="status-badge">
              <span>{{ t('app.secureGateway') }}</span>
            </div>
          </div>
        </header>

        <!-- Tab Navigation -->
        <nav class="tab-nav">
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'upload' }"
            @click="activeTab = 'upload'"
          >
            <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
            </svg>
            {{ t('tabs.upload') }}
          </button>
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'generate' }"
            @click="activeTab = 'generate'"
          >
            <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
            </svg>
            {{ t('tabs.generate') }}
          </button>
        </nav>

        <!-- Content Area -->
        <div class="panel-content">
          <!-- ==================== UPLOAD TAB ==================== -->
          <div v-if="activeTab === 'upload'" class="tab-content">
            <!-- File Upload Zone -->
            <div class="form-group">
              <label class="form-label">{{ t('upload.selectImage') }}</label>
              <div
                class="upload-zone"
                :class="{ dragging: isDragging, 'has-file': file }"
                @dragover="onDragOver"
                @dragleave="onDragLeave"
                @drop="onDrop"
              >
                <input
                  type="file"
                  accept="image/*"
                  @change="onFileChange"
                />
                <div v-if="!file">
                  <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
                  </svg>
                  <p class="upload-text">Drop image here or click to browse</p>
                  <p class="upload-hint">PNG, JPG, WebP supported</p>
                </div>
                <div v-else class="file-preview">
                  <img v-if="filePreviewUrl" :src="filePreviewUrl" alt="Preview" class="preview-image" />
                  <p class="file-name">{{ file.name }}</p>
                </div>
              </div>
            </div>

            <!-- Split Mode Selection -->
            <div class="form-group">
              <label class="form-label">{{ t('upload.splitMode') }}</label>
              <div class="mode-grid">
                <button
                  class="mode-card"
                  :class="{ active: uploadSplitMode === 'auto' }"
                  @click="uploadSplitMode = 'auto'"
                >
                  <div class="mode-card-header">
                    <svg class="mode-card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                    </svg>
                    <span class="mode-card-title">{{ t('upload.splitModeAuto') }}</span>
                  </div>
                  <p class="mode-card-desc">{{ t('upload.splitModeAutoDesc') }}</p>
                </button>
                <button
                  class="mode-card"
                  :class="{ active: uploadSplitMode === 'grid' }"
                  @click="uploadSplitMode = 'grid'"
                >
                  <div class="mode-card-header">
                    <svg class="mode-card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <rect x="3" y="3" width="7" height="7"/>
                      <rect x="14" y="3" width="7" height="7"/>
                      <rect x="14" y="14" width="7" height="7"/>
                      <rect x="3" y="14" width="7" height="7"/>
                    </svg>
                    <span class="mode-card-title">{{ t('upload.splitModeGrid') }}</span>
                  </div>
                  <p class="mode-card-desc">{{ t('upload.splitModeGridDesc') }}</p>
                </button>
              </div>
            </div>

            <!-- Advanced Parameters Accordion -->
            <div class="accordion">
              <button
                class="accordion-header"
                :class="{ open: showUploadAdvancedParams }"
                @click="showUploadAdvancedParams = !showUploadAdvancedParams"
              >
                <span>{{ t('params.title') }}</span>
                <svg class="accordion-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M6 9l6 6 6-6"/>
                </svg>
              </button>

              <div v-if="showUploadAdvancedParams" class="accordion-content">
                <!-- Auto Detect Mode Parameters -->
                <template v-if="uploadSplitMode === 'auto'">
                  <div class="params-section">
                    <h4 class="params-title">{{ t('params.processing') }}</h4>

                    <div class="range-group">
                      <div class="range-header">
                        <span class="range-label">{{ t('params.distanceThreshold.label') }}</span>
                        <span class="range-value">{{ uploadDistanceThreshold }}</span>
                      </div>
                      <input type="range" v-model.number="uploadDistanceThreshold" :min="10" :max="500" :step="10" />
                      <p class="range-desc">{{ t('params.distanceThreshold.description') }}</p>
                    </div>

                    <div class="range-group">
                      <div class="range-header">
                        <span class="range-label">{{ t('params.sizeRatioThreshold.label') }}</span>
                        <span class="range-value">{{ uploadSizeRatioThreshold.toFixed(2) }}</span>
                      </div>
                      <input type="range" v-model.number="uploadSizeRatioThreshold" :min="0.1" :max="1.0" :step="0.05" />
                      <p class="range-desc">{{ t('params.sizeRatioThreshold.description') }}</p>
                    </div>

                    <div class="range-group">
                      <div class="range-header">
                        <span class="range-label">{{ t('params.alphaThreshold.label') }}</span>
                        <span class="range-value">{{ uploadAlphaThreshold }}</span>
                      </div>
                      <input type="range" v-model.number="uploadAlphaThreshold" :min="1" :max="254" :step="1" />
                      <p class="range-desc">{{ t('params.alphaThreshold.description') }}</p>
                    </div>

                    <div class="range-group">
                      <div class="range-header">
                        <span class="range-label">{{ t('params.minAreaRatio.label') }}</span>
                        <span class="range-value">{{ uploadMinAreaRatio.toFixed(4) }}</span>
                      </div>
                      <input type="range" v-model.number="uploadMinAreaRatio" :min="0.0001" :max="0.1" :step="0.0001" />
                      <p class="range-desc">{{ t('params.minAreaRatio.description') }}</p>
                    </div>

                    <div class="range-group">
                      <div class="range-header">
                        <span class="range-label">{{ t('params.maxAreaRatio.label') }}</span>
                        <span class="range-value">{{ uploadMaxAreaRatio.toFixed(2) }}</span>
                      </div>
                      <input type="range" v-model.number="uploadMaxAreaRatio" :min="0.05" :max="0.9" :step="0.05" />
                      <p class="range-desc">{{ t('params.maxAreaRatio.description') }}</p>
                    </div>
                  </div>
                </template>

                <!-- Grid Mode Parameters -->
                <template v-else>
                  <div class="params-section">
                    <h4 class="params-title">{{ t('params.gridParams') }}</h4>

                    <div class="toggle-group">
                      <span class="toggle-label">{{ t('params.autoDetect.label') }}</span>
                      <button
                        class="toggle-switch"
                        :class="{ active: gridAutoDetect }"
                        @click="gridAutoDetect = !gridAutoDetect"
                      ></button>
                    </div>
                    <p class="range-desc" style="margin-top: -0.5rem; margin-bottom: 1rem;">{{ t('params.autoDetect.description') }}</p>

                    <div v-if="!gridAutoDetect" class="grid-inputs">
                      <div class="range-group">
                        <div class="range-header">
                          <span class="range-label">{{ t('params.gridRows.label') }}</span>
                          <span class="range-value">{{ gridRows }}</span>
                        </div>
                        <input type="range" v-model.number="gridRows" :min="1" :max="20" :step="1" />
                      </div>

                      <div class="range-group">
                        <div class="range-header">
                          <span class="range-label">{{ t('params.gridCols.label') }}</span>
                          <span class="range-value">{{ gridCols }}</span>
                        </div>
                        <input type="range" v-model.number="gridCols" :min="1" :max="20" :step="1" />
                      </div>
                    </div>

                    <div class="range-group">
                      <div class="range-header">
                        <span class="range-label">{{ t('params.gridPadding.label') }}</span>
                        <span class="range-value">{{ gridPadding }}</span>
                      </div>
                      <input type="range" v-model.number="gridPadding" :min="0" :max="20" :step="1" />
                      <p class="range-desc">{{ t('params.gridPadding.description') }}</p>
                    </div>

                    <template v-if="gridAutoDetect">
                      <div class="range-group">
                        <div class="range-header">
                          <span class="range-label">{{ t('params.lineThreshold.label') }}</span>
                          <span class="range-value">{{ gridLineThreshold }}</span>
                        </div>
                        <input type="range" v-model.number="gridLineThreshold" :min="10" :max="200" :step="10" />
                        <p class="range-desc">{{ t('params.lineThreshold.description') }}</p>
                      </div>

                      <div class="range-group">
                        <div class="range-header">
                          <span class="range-label">{{ t('params.minLineLengthRatio.label') }}</span>
                          <span class="range-value">{{ gridMinLineLengthRatio.toFixed(2) }}</span>
                        </div>
                        <input type="range" v-model.number="gridMinLineLengthRatio" :min="0.1" :max="1.0" :step="0.05" />
                        <p class="range-desc">{{ t('params.minLineLengthRatio.description') }}</p>
                      </div>
                    </template>
                  </div>
                </template>

                <!-- Custom Output Sizes -->
                <div class="params-section output-sizes-section">
                  <div class="toggle-group">
                    <h4 class="params-title" style="margin: 0;">{{ t('params.outputSizes.title') }}</h4>
                    <button
                      class="toggle-switch"
                      :class="{ active: useCustomSizes }"
                      @click="useCustomSizes = !useCustomSizes"
                    ></button>
                  </div>
                  <p class="range-desc">{{ t('params.outputSizes.description') }}</p>

                  <div v-if="useCustomSizes" class="size-editor">
                    <div v-for="(size, index) in customSizes" :key="index" class="size-row">
                      <input
                        v-model="size.name"
                        :placeholder="t('params.outputSizes.namePlaceholder')"
                        class="size-input name"
                      />
                      <input
                        v-model.number="size.width"
                        type="number"
                        min="16"
                        max="1024"
                        class="size-input"
                      />
                      <span class="size-separator">×</span>
                      <input
                        v-model.number="size.height"
                        type="number"
                        min="16"
                        max="1024"
                        class="size-input"
                      />
                      <button
                        v-if="customSizes.length > 1"
                        class="btn-icon"
                        @click="removeCustomSize(index)"
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <path d="M18 6L6 18M6 6l12 12"/>
                        </svg>
                      </button>
                    </div>
                    <button class="btn-add-size" @click="addCustomSize">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 5v14M5 12h14"/>
                      </svg>
                      {{ t('params.outputSizes.addSize') }}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Submit Button -->
            <button
              v-if="file"
              class="btn-primary"
              :class="{ loading: ['UPLOADING', 'PENDING', 'PROCESSING'].includes(uploadStatus) }"
              :disabled="['UPLOADING', 'PENDING', 'PROCESSING', 'SUCCESS'].includes(uploadStatus)"
              @click="uploadFile"
            >
              <span v-if="['UPLOADING', 'PENDING', 'PROCESSING'].includes(uploadStatus)" class="spinner"></span>
              <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M5 12h14M12 5l7 7-7 7"/>
              </svg>
              {{ uploadStatus === 'IDLE' ? t('upload.startProcessing') : t('upload.processing') }}
            </button>

            <!-- Upload Status Display -->
            <div v-if="uploadStatus !== 'IDLE'" class="status-panel">
              <div class="status-header">
                <span class="status-label">{{ t('status.label') }}</span>
                <span
                  class="status-indicator"
                  :class="{
                    success: uploadStatus === 'SUCCESS',
                    error: uploadStatus === 'FAILURE',
                    pending: !['SUCCESS', 'FAILURE'].includes(uploadStatus)
                  }"
                >
                  {{ getStatusText(uploadStatus) }}
                </span>
              </div>

              <div v-if="['UPLOADING', 'PENDING', 'PROCESSING'].includes(uploadStatus)" class="progress-bar"></div>

              <div v-if="uploadStatus === 'FAILURE'" class="error-message">
                {{ t('error.prefix') }} {{ uploadError }}
              </div>

              <div v-if="uploadStatus === 'SUCCESS'" class="success-result">
                <p class="success-message">{{ t('result.complete') }}</p>
                <a :href="uploadDownloadLink" class="btn-success" download>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/>
                  </svg>
                  {{ t('result.downloadZip') }}
                </a>
              </div>
            </div>
          </div>

          <!-- ==================== GENERATE TAB ==================== -->
          <div v-if="activeTab === 'generate'" class="tab-content">
            <!-- Mode Toggle -->
            <div class="form-group">
              <label class="form-label">{{ t('generate.mode') }}</label>
              <div class="toggle-group" style="padding: 0;">
                <span class="toggle-hint">{{ useReferenceImage ? t('generate.imageToImage') : t('generate.textToImage') }}</span>
                <button
                  class="toggle-switch"
                  :class="{ active: useReferenceImage }"
                  @click="useReferenceImage = !useReferenceImage"
                ></button>
              </div>
            </div>

            <!-- Reference Image Upload -->
            <div v-if="useReferenceImage" class="form-group">
              <label class="form-label">{{ t('generate.referenceImage') }}</label>
              <div class="upload-zone" :class="{ 'has-file': referenceFile }">
                <div v-if="referencePreviewUrl" class="reference-preview">
                  <img :src="referencePreviewUrl" alt="Reference" />
                  <button class="btn-remove" @click="clearReferenceImage">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M18 6L6 18M6 6l12 12"/>
                    </svg>
                  </button>
                </div>
                <div v-else>
                  <input
                    type="file"
                    accept="image/*"
                    @change="onReferenceFileChange"
                  />
                  <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <rect x="3" y="3" width="18" height="18" rx="2"/>
                    <circle cx="8.5" cy="8.5" r="1.5"/>
                    <path d="M21 15l-5-5L5 21"/>
                  </svg>
                  <p class="upload-text">{{ t('generate.uploadReference') }}</p>
                </div>
              </div>
            </div>

            <!-- Prompt Input -->
            <div class="form-group">
              <label class="form-label">
                {{ useReferenceImage ? t('generate.editInstruction') : t('generate.describeSprite') }}
              </label>
              <textarea
                v-model="prompt"
                class="form-textarea"
                rows="4"
                :placeholder="useReferenceImage ? t('generate.editPlaceholder') : t('generate.promptPlaceholder')"
              ></textarea>
            </div>

            <!-- Model Selection -->
            <div class="form-group">
              <label class="form-label">{{ t('generate.model') }}</label>
              <select v-model="model" class="form-select">
                <option v-for="opt in modelOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
            </div>

            <!-- Advanced Parameters Accordion -->
            <div class="accordion">
              <button
                class="accordion-header"
                :class="{ open: showAdvancedParams }"
                @click="showAdvancedParams = !showAdvancedParams"
              >
                <span>{{ t('params.title') }}</span>
                <svg class="accordion-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M6 9l6 6 6-6"/>
                </svg>
              </button>

              <div v-if="showAdvancedParams" class="accordion-content">
                <!-- Generation Parameters -->
                <div class="params-section">
                  <h4 class="params-title">{{ t('params.generation') }}</h4>

                  <div class="range-group">
                    <div class="range-header">
                      <span class="range-label">{{ t('params.temperature.label') }}</span>
                      <span class="range-value">{{ temperature.toFixed(1) }}</span>
                    </div>
                    <input type="range" v-model.number="temperature" :min="0" :max="2" :step="0.1" />
                    <p class="range-desc">{{ t('params.temperature.description') }}</p>
                  </div>
                </div>

                <!-- Processing Parameters -->
                <div class="params-section">
                  <h4 class="params-title">{{ t('params.processing') }}</h4>

                  <div class="range-group">
                    <div class="range-header">
                      <span class="range-label">{{ t('params.distanceThreshold.label') }}</span>
                      <span class="range-value">{{ distanceThreshold }}</span>
                    </div>
                    <input type="range" v-model.number="distanceThreshold" :min="10" :max="500" :step="10" />
                    <p class="range-desc">{{ t('params.distanceThreshold.description') }}</p>
                  </div>

                  <div class="range-group">
                    <div class="range-header">
                      <span class="range-label">{{ t('params.sizeRatioThreshold.label') }}</span>
                      <span class="range-value">{{ sizeRatioThreshold.toFixed(2) }}</span>
                    </div>
                    <input type="range" v-model.number="sizeRatioThreshold" :min="0.1" :max="1.0" :step="0.05" />
                    <p class="range-desc">{{ t('params.sizeRatioThreshold.description') }}</p>
                  </div>

                  <div class="range-group">
                    <div class="range-header">
                      <span class="range-label">{{ t('params.alphaThreshold.label') }}</span>
                      <span class="range-value">{{ alphaThreshold }}</span>
                    </div>
                    <input type="range" v-model.number="alphaThreshold" :min="1" :max="254" :step="1" />
                    <p class="range-desc">{{ t('params.alphaThreshold.description') }}</p>
                  </div>

                  <div class="range-group">
                    <div class="range-header">
                      <span class="range-label">{{ t('params.minAreaRatio.label') }}</span>
                      <span class="range-value">{{ minAreaRatio.toFixed(4) }}</span>
                    </div>
                    <input type="range" v-model.number="minAreaRatio" :min="0.0001" :max="0.1" :step="0.0001" />
                    <p class="range-desc">{{ t('params.minAreaRatio.description') }}</p>
                  </div>

                  <div class="range-group">
                    <div class="range-header">
                      <span class="range-label">{{ t('params.maxAreaRatio.label') }}</span>
                      <span class="range-value">{{ maxAreaRatio.toFixed(2) }}</span>
                    </div>
                    <input type="range" v-model.number="maxAreaRatio" :min="0.05" :max="0.9" :step="0.05" />
                    <p class="range-desc">{{ t('params.maxAreaRatio.description') }}</p>
                  </div>
                </div>

                <!-- Custom Output Sizes -->
                <div class="params-section output-sizes-section">
                  <div class="toggle-group">
                    <h4 class="params-title" style="margin: 0;">{{ t('params.outputSizes.title') }}</h4>
                    <button
                      class="toggle-switch"
                      :class="{ active: useCustomSizes }"
                      @click="useCustomSizes = !useCustomSizes"
                    ></button>
                  </div>
                  <p class="range-desc">{{ t('params.outputSizes.description') }}</p>

                  <div v-if="useCustomSizes" class="size-editor">
                    <div v-for="(size, index) in customSizes" :key="index" class="size-row">
                      <input
                        v-model="size.name"
                        :placeholder="t('params.outputSizes.namePlaceholder')"
                        class="size-input name"
                      />
                      <input
                        v-model.number="size.width"
                        type="number"
                        min="16"
                        max="1024"
                        class="size-input"
                      />
                      <span class="size-separator">×</span>
                      <input
                        v-model.number="size.height"
                        type="number"
                        min="16"
                        max="1024"
                        class="size-input"
                      />
                      <button
                        v-if="customSizes.length > 1"
                        class="btn-icon"
                        @click="removeCustomSize(index)"
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <path d="M18 6L6 18M6 6l12 12"/>
                        </svg>
                      </button>
                    </div>
                    <button class="btn-add-size" @click="addCustomSize">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 5v14M5 12h14"/>
                      </svg>
                      {{ t('params.outputSizes.addSize') }}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Generate Button -->
            <button
              class="btn-primary"
              :class="{ loading: ['UPLOADING', 'PENDING', 'GENERATING', 'PROCESSING', 'PACKAGING'].includes(generateStatus) }"
              :disabled="!prompt.trim() || ['SUCCESS'].includes(generateStatus) || (useReferenceImage && !referenceFile)"
              @click="generateSprite"
            >
              <span v-if="['UPLOADING', 'PENDING', 'GENERATING', 'PROCESSING', 'PACKAGING'].includes(generateStatus)" class="spinner"></span>
              <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
              </svg>
              {{ generateStatus === 'IDLE' ? (useReferenceImage ? t('generate.generateFromRef') : t('generate.generateSprite')) : t('generate.generating') }}
            </button>

            <!-- Generate Status Display -->
            <div v-if="generateStatus !== 'IDLE'" class="status-panel">
              <div class="status-header">
                <span class="status-label">{{ t('status.label') }}</span>
                <span
                  class="status-indicator"
                  :class="{
                    success: generateStatus === 'SUCCESS',
                    error: generateStatus === 'FAILURE',
                    pending: !['SUCCESS', 'FAILURE'].includes(generateStatus)
                  }"
                >
                  {{ getStatusText(generateStatus) }}
                </span>
              </div>

              <div v-if="['UPLOADING', 'PENDING', 'GENERATING', 'PROCESSING', 'PACKAGING'].includes(generateStatus)" class="progress-bar"></div>

              <div v-if="generateStatus === 'FAILURE'" class="error-message">
                {{ t('error.prefix') }} {{ generateError }}
              </div>

              <div v-if="generateStatus === 'SUCCESS'" class="success-result">
                <p class="success-message">{{ t('result.complete') }}</p>
                <a :href="generateDownloadLink" class="btn-success" download>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/>
                  </svg>
                  {{ t('result.downloadSprites') }}
                </a>
                <button class="btn-secondary" style="width: 100%; margin-top: 0.75rem;" @click="resetGenerateState">
                  {{ t('result.generateAnother') }}
                </button>
              </div>
            </div>

            <!-- Info Alert -->
            <div class="info-alert">
              <svg class="info-alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <path d="M12 16v-4M12 8h.01"/>
              </svg>
              <div class="info-alert-content">
                <p class="info-alert-title">{{ t('info.title') }}</p>
                <p class="info-alert-text">{{ useReferenceImage ? t('info.imageToImage') : t('info.textToImage') }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem 1rem;
  position: relative;
}

.main-wrapper {
  width: 100%;
  max-width: 680px;
  position: relative;
  z-index: 1;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.tab-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.params-section {
  margin-bottom: 1.5rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid rgba(0, 229, 224, 0.15);
}

.params-section:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.params-title {
  font-family: var(--font-pixel);
  font-size: 0.875rem;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.15em;
  margin: 0 0 1rem 0;
}

.output-sizes-section {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(0, 229, 224, 0.15);
  border-bottom: none;
}

.grid-inputs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.toggle-hint {
  font-family: var(--font-pixel);
  font-size: 0.9375rem;
  color: var(--text-primary);
}

.file-preview {
  text-align: center;
}

.preview-image {
  max-height: 150px;
  max-width: 100%;
  border-radius: 4px;
  border: 1px solid rgba(0, 229, 224, 0.4);
  margin-bottom: 0.75rem;
}

.file-name {
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  color: var(--neon-cyan);
  margin: 0;
  word-break: break-all;
}

.upload-zone.has-file {
  border-style: solid;
  border-color: rgba(0, 229, 224, 0.5);
}

/* Responsive */
@media (max-width: 640px) {
  .app-container {
    padding: 1rem 0.5rem;
  }

  .header-controls {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }

  .grid-inputs {
    grid-template-columns: 1fr;
  }

  .size-row {
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .size-input {
    width: 60px;
  }

  .size-input.name {
    width: 100%;
  }
}
</style>
