<template>
  <TerminalLayout>
    <div class="fade-in image-gen-container">
      <!-- Header -->
      <div class="flex items-center gap-3 mb-6">
        <span class="text-xl">▤</span>
        <h2 class="text-xl font-bold glow-text">AI 生图</h2>
        <span class="text-xs opacity-50 ml-2">// Image Generation</span>
      </div>

      <!-- Main Content Grid -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Left Panel: Controls -->
        <div class="content-card p-6">
          <!-- Mode Switch -->
          <div class="mode-switch mb-6">
            <button
              v-for="m in modes"
              :key="m.value"
              class="mode-btn"
              :class="{ active: mode === m.value }"
              @click="mode = m.value"
            >
              <span class="mode-icon">{{ m.icon }}</span>
              <span>{{ m.label }}</span>
            </button>
          </div>

          <!-- Image Upload (for edit mode) -->
          <div v-if="mode === 'edit'" class="upload-section mb-6">
            <label class="form-label">参考图片</label>
            <div
              class="upload-area"
              :class="{ 'has-image': uploadedImage }"
              @click="triggerUpload"
              @drop.prevent="handleDrop"
              @dragover.prevent="isDragging = true"
              @dragleave.prevent="isDragging = false"
            >
              <input
                ref="fileInput"
                type="file"
                accept="image/*"
                class="hidden"
                @change="handleFileChange"
              />
              <div v-if="!uploadedImage" class="upload-placeholder">
                <span class="upload-icon">+</span>
                <span class="upload-text">点击或拖拽上传图片</span>
                <span class="upload-hint">支持 PNG, JPG, WebP</span>
              </div>
              <div v-else class="upload-preview">
                <img :src="uploadedImage" alt="Uploaded" />
                <button class="remove-btn" @click.stop="removeImage">R</button>
              </div>
            </div>
          </div>

          <!-- Prompt Input -->
          <div class="form-group mb-5">
            <label class="form-label">
              <span v-if="mode === 'generate'">描述你想要的图片</span>
              <span v-else>描述如何修改图片</span>
            </label>
            <textarea
              v-model="form.prompt"
              class="prompt-input"
              :placeholder="mode === 'generate' ? '一只在草地上奔跑的金毛犬，阳光明媚，照片级真实感...' : '让猫咪戴上太阳镜，背景换成海滩...'"
              rows="4"
            ></textarea>
            <div class="prompt-actions">
              <button
                v-for="tag in quickTags"
                :key="tag"
                class="tag-btn"
                @click="appendTag(tag)"
              >
                + {{ tag }}
              </button>
            </div>
          </div>

          <!-- Parameters Grid -->
          <div class="params-grid mb-6">
            <div class="param-item">
              <label class="param-label">模型</label>
              <select v-model="form.model" class="param-select">
                <option v-for="m in imageModels" :key="m.id" :value="m.id">
                  {{ m.name }}
                </option>
              </select>
            </div>

            <div class="param-item">
              <label class="param-label">尺寸</label>
              <select v-model="form.size" class="param-select">
                <option v-for="s in currentSizes" :key="s" :value="s">
                  {{ s }}
                </option>
              </select>
            </div>

            <div class="param-item">
              <label class="param-label">质量</label>
              <select v-model="form.quality" class="param-select">
                <option value="standard">标准</option>
                <option value="hd">高清</option>
              </select>
            </div>

            <div class="param-item">
              <label class="param-label">风格</label>
              <select v-model="form.style" class="param-select">
                <option value="vivid">生动</option>
                <option value="natural">自然</option>
              </select>
            </div>
          </div>

          <!-- Generate Button -->
          <TerminalButton
            type="primary"
            size="lg"
            :loading="loading"
            :disabled="!canGenerate"
            class="w-full generate-btn"
            @click="generateImage"
          >
            <span v-if="loading" class="flex items-center justify-center gap-2">
              <span class="animate-pulse">■</span>
              生成中...
            </span>
            <span v-else>
              <span v-if="mode === 'generate'">▸ 开始生成</span>
              <span v-else>▸ 修改图片</span>
            </span>
          </TerminalButton>

          <!-- Error Message -->
          <div v-if="error" class="error-box mt-4">
            <span class="error-icon">X</span>
            {{ error }}
          </div>
        </div>

        <!-- Right Panel: Results -->
        <div class="content-card p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-sm font-bold text-green-400">生成结果</h3>
            <span v-if="generatedImages.length > 0" class="text-xs opacity-50">
              {{ generatedImages.length }} 张图片
            </span>
          </div>

          <!-- Empty State -->
          <div v-if="generatedImages.length === 0 && !loading" class="empty-state">
            <div class="empty-icon">▤</div>
            <div class="empty-text">等待生成...</div>
            <div class="empty-hint">在左侧输入描述，点击生成按钮</div>
          </div>

          <!-- Loading State -->
          <div v-if="loading && generatedImages.length === 0" class="loading-state">
            <div class="loading-animation">
              <span v-for="i in 3" :key="i" class="loading-dot" :style="{ animationDelay: `${i * 0.2}s` }">■</span>
            </div>
            <div class="loading-text">AI 正在创作...</div>
            <div class="loading-hint">通常需要 30-90 秒</div>
          </div>

          <!-- Image Grid -->
          <div v-if="generatedImages.length > 0" class="result-grid">
            <div
              v-for="(img, index) in generatedImages"
              :key="index"
              class="result-item"
            >
              <div class="image-frame">
                <img
                  :src="img.url"
                  :alt="`Generated ${index + 1}`"
                  @load="onImageLoad"
                  @click="openPreview(img.url)"
                />
                <div class="image-overlay">
                  <button class="overlay-btn" @click="openPreview(img.url)">
                    查看
                  </button>
                  <button class="overlay-btn" @click="downloadImage(img.url, index)">
                    下载
                  </button>
                  <button class="overlay-btn" @click="useAsReference(img.url)">
                    以此为参考
                  </button>
                </div>
              </div>
              <div v-if="img.revised_prompt" class="revised-prompt">
                {{ img.revised_prompt }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- History Section -->
      <div v-if="history.length > 0" class="content-card p-6 mt-6">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-sm font-bold text-green-400">历史记录</h3>
          <button class="text-xs opacity-50 hover:opacity-100" @click="clearHistory">
            清空
          </button>
        </div>
        <div class="history-grid">
          <div
            v-for="(item, index) in history"
            :key="index"
            class="history-item"
            @click="restoreFromHistory(item)"
          >
            <img :src="item.thumbnail" alt="History" />
            <div class="history-meta">
              <div class="history-prompt">{{ item.prompt }}</div>
              <div class="history-time">{{ item.time }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Preview Modal -->
    <div v-if="previewUrl" class="preview-modal" @click="closePreview">
      <div class="preview-content" @click.stop>
        <img :src="previewUrl" alt="Preview" />
        <button class="preview-close" @click="closePreview">R</button>
      </div>
    </div>
  </TerminalLayout>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import TerminalLayout from '@/components/TerminalLayout.vue'
import TerminalButton from '@/components/TerminalButton.vue'
import api from '@/api'

interface ImageModel {
  id: string
  name: string
  sizes: string[]
}

interface GeneratedImage {
  url: string
  revised_prompt?: string
}

interface HistoryItem {
  prompt: string
  thumbnail: string
  time: string
  params: any
}

const mode = ref<'generate' | 'edit'>('generate')
const modes = [
  { value: 'generate' as const, label: '文生图', icon: '▸' },
  { value: 'edit' as const, label: '图生图', icon: '◆' }
]

const loading = ref(false)
const error = ref('')
const generatedImages = ref<GeneratedImage[]>([])
const imageModels = ref<ImageModel[]>([])
const uploadedImage = ref('')
const fileInput = ref<HTMLInputElement>()
const isDragging = ref(false)
const previewUrl = ref('')
const history = ref<HistoryItem[]>([])

const quickTags = ['高清', '照片级', '卡通', '油画', '赛博朋克', '水墨']

const form = reactive({
  model: 'gpt-image-2',
  prompt: '',
  size: '1024x1024',
  quality: 'standard',
  style: 'vivid'
})

const currentSizes = computed(() => {
  const model = imageModels.value.find(m => m.id === form.model)
  return model?.sizes || ['1024x1024']
})

const canGenerate = computed(() => {
  if (!form.prompt.trim()) return false
  if (mode.value === 'edit' && !uploadedImage.value) return false
  return true
})

watch(() => form.model, () => {
  const model = imageModels.value.find(m => m.id === form.model)
  if (model && !model.sizes.includes(form.size)) {
    form.size = model.sizes[0]
  }
})

onMounted(async () => {
  try {
    const res = await api.get('/api/image-models')
    if (res.data.success) {
      imageModels.value = res.data.data
      if (imageModels.value.length > 0) {
        form.model = imageModels.value[0].id
        form.size = imageModels.value[0].sizes[0]
      }
    }
  } catch (e) {
    console.error('Failed to load image models:', e)
  }

  // Load history from localStorage
  const saved = localStorage.getItem('image-gen-history')
  if (saved) {
    try {
      history.value = JSON.parse(saved)
    } catch {}
  }
})

function triggerUpload() {
  fileInput.value?.click()
}

function handleFileChange(e: Event) {
  const files = (e.target as HTMLInputElement).files
  if (files && files[0]) {
    readFile(files[0])
  }
}

function handleDrop(e: DragEvent) {
  isDragging.value = false
  const files = e.dataTransfer?.files
  if (files && files[0]) {
    readFile(files[0])
  }
}

function readFile(file: File) {
  if (!file.type.startsWith('image/')) {
    error.value = '请上传图片文件'
    return
  }
  const reader = new FileReader()
  reader.onload = (e) => {
    uploadedImage.value = e.target?.result as string
    error.value = ''
  }
  reader.readAsDataURL(file)
}

function removeImage() {
  uploadedImage.value = ''
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

function appendTag(tag: string) {
  form.prompt = form.prompt ? `${form.prompt}, ${tag}` : tag
}

async function generateImage() {
  if (!canGenerate.value) return

  loading.value = true
  error.value = ''
  generatedImages.value = []

  try {
    let res
    if (mode.value === 'generate') {
      res = await api.post('/api/image-generations', {
        model: form.model,
        prompt: form.prompt,
        n: 1,
        size: form.size,
        quality: form.quality,
        style: form.style
      })
    } else {
      res = await api.post('/api/image-edits', {
        model: form.model,
        prompt: form.prompt,
        image: uploadedImage.value,
        size: form.size
      })
    }

    if (res.data.success && res.data.data?.data) {
      generatedImages.value = res.data.data.data
      addToHistory()
    } else {
      error.value = '生成失败：未返回图片数据'
    }
  } catch (e: any) {
    error.value = e.response?.data?.detail || '生成失败，请检查渠道配置'
  } finally {
    loading.value = false
  }
}

function addToHistory() {
  if (generatedImages.value.length === 0) return
  const item: HistoryItem = {
    prompt: form.prompt,
    thumbnail: generatedImages.value[0].url,
    time: new Date().toLocaleString(),
    params: { ...form }
  }
  history.value.unshift(item)
  if (history.value.length > 10) {
    history.value = history.value.slice(0, 10)
  }
  localStorage.setItem('image-gen-history', JSON.stringify(history.value))
}

function restoreFromHistory(item: HistoryItem) {
  form.prompt = item.prompt
  if (item.params) {
    form.model = item.params.model || form.model
    form.size = item.params.size || form.size
    form.quality = item.params.quality || form.quality
    form.style = item.params.style || form.style
  }
}

function clearHistory() {
  history.value = []
  localStorage.removeItem('image-gen-history')
}

function onImageLoad() {
  // Image loaded
}

function openPreview(url: string) {
  previewUrl.value = url
}

function closePreview() {
  previewUrl.value = ''
}

function downloadImage(url: string, index: number) {
  const link = document.createElement('a')
  link.href = url
  link.download = `generated-${index + 1}.png`
  link.target = '_blank'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

function useAsReference(url: string) {
  mode.value = 'edit'
  uploadedImage.value = url
}
</script>

<style scoped>
.image-gen-container {
  padding: 1.5rem;
  max-width: 1400px;
  margin: 0 auto;
}

/* Mode Switch */
.mode-switch {
  display: flex;
  gap: 0.5rem;
  background: rgba(0, 255, 65, 0.05);
  padding: 4px;
  border-radius: 8px;
  border: 1px solid rgba(0, 255, 65, 0.1);
}

.mode-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: transparent;
  border: none;
  color: rgba(0, 255, 65, 0.5);
  font-size: 0.875rem;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s;
}

.mode-btn:hover {
  color: rgba(0, 255, 65, 0.8);
}

.mode-btn.active {
  background: rgba(0, 255, 65, 0.15);
  color: #00ff41;
}

.mode-icon {
  font-size: 0.75rem;
}

/* Upload Section */
.upload-area {
  border: 2px dashed rgba(0, 255, 65, 0.2);
  border-radius: 12px;
  padding: 2rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  min-height: 160px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-area:hover {
  border-color: rgba(0, 255, 65, 0.4);
  background: rgba(0, 255, 65, 0.03);
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.upload-icon {
  font-size: 2rem;
  color: rgba(0, 255, 65, 0.3);
}

.upload-text {
  font-size: 0.875rem;
  color: rgba(0, 255, 65, 0.6);
}

.upload-hint {
  font-size: 0.75rem;
  color: rgba(0, 255, 65, 0.3);
}

.upload-preview {
  position: relative;
  width: 100%;
  max-width: 300px;
}

.upload-preview img {
  width: 100%;
  border-radius: 8px;
  display: block;
}

.remove-btn {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 24px;
  height: 24px;
  background: #ef4444;
  color: white;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  font-size: 0.625rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Form Elements */
.form-label {
  display: block;
  font-size: 0.8125rem;
  font-weight: 500;
  color: rgba(0, 255, 65, 0.7);
  margin-bottom: 0.5rem;
}

.prompt-input {
  width: 100%;
  padding: 1rem;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(0, 255, 65, 0.15);
  border-radius: 8px;
  color: #00ff41;
  font-size: 0.875rem;
  font-family: inherit;
  resize: vertical;
  transition: border-color 0.2s;
}

.prompt-input:focus {
  outline: none;
  border-color: rgba(0, 255, 65, 0.4);
}

.prompt-input::placeholder {
  color: rgba(0, 255, 65, 0.25);
}

.prompt-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.tag-btn {
  padding: 0.25rem 0.75rem;
  background: rgba(0, 255, 65, 0.05);
  border: 1px solid rgba(0, 255, 65, 0.15);
  border-radius: 4px;
  color: rgba(0, 255, 65, 0.6);
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
}

.tag-btn:hover {
  background: rgba(0, 255, 65, 0.1);
  border-color: rgba(0, 255, 65, 0.3);
  color: #00ff41;
}

/* Parameters */
.params-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.param-item {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.param-label {
  font-size: 0.75rem;
  color: rgba(0, 255, 65, 0.5);
}

.param-select {
  padding: 0.625rem 0.75rem;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(0, 255, 65, 0.15);
  border-radius: 6px;
  color: #00ff41;
  font-size: 0.8125rem;
  cursor: pointer;
}

.param-select:focus {
  outline: none;
  border-color: rgba(0, 255, 65, 0.4);
}

/* Generate Button */
.generate-btn {
  font-size: 0.9375rem;
  letter-spacing: 0.05em;
}

/* Error Box */
.error-box {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem 1rem;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 8px;
  color: #ef4444;
  font-size: 0.8125rem;
}

.error-icon {
  font-weight: bold;
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  text-align: center;
}

.empty-icon {
  font-size: 3rem;
  color: rgba(0, 255, 65, 0.1);
  margin-bottom: 1rem;
}

.empty-text {
  font-size: 1rem;
  color: rgba(0, 255, 65, 0.4);
  margin-bottom: 0.5rem;
}

.empty-hint {
  font-size: 0.75rem;
  color: rgba(0, 255, 65, 0.25);
}

/* Loading State */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
}

.loading-animation {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.loading-dot {
  color: #00ff41;
  animation: bounce 1.4s infinite ease-in-out;
}

.loading-text {
  font-size: 1rem;
  color: rgba(0, 255, 65, 0.6);
  margin-bottom: 0.5rem;
}

.loading-hint {
  font-size: 0.75rem;
  color: rgba(0, 255, 65, 0.3);
}

@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-10px); }
}

/* Result Grid */
.result-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 1rem;
}

.result-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.image-frame {
  position: relative;
  aspect-ratio: 1;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
}

.image-frame img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s;
}

.image-frame:hover img {
  transform: scale(1.02);
}

.image-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  opacity: 0;
  transition: opacity 0.3s;
}

.image-frame:hover .image-overlay {
  opacity: 1;
}

.overlay-btn {
  padding: 0.5rem 1rem;
  background: rgba(0, 255, 65, 0.15);
  border: 1px solid rgba(0, 255, 65, 0.3);
  border-radius: 4px;
  color: #00ff41;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
}

.overlay-btn:hover {
  background: rgba(0, 255, 65, 0.25);
}

.revised-prompt {
  font-size: 0.75rem;
  color: rgba(0, 255, 65, 0.4);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* History */
.history-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 1rem;
}

.history-item {
  cursor: pointer;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.2s;
}

.history-item:hover {
  box-shadow: 0 0 10px rgba(0, 255, 65, 0.2);
}

.history-item img {
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  display: block;
}

.history-meta {
  padding: 0.5rem;
  background: rgba(0, 0, 0, 0.4);
}

.history-prompt {
  font-size: 0.6875rem;
  color: rgba(0, 255, 65, 0.6);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.history-time {
  font-size: 0.625rem;
  color: rgba(0, 255, 65, 0.3);
  margin-top: 0.25rem;
}

/* Preview Modal */
.preview-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 2rem;
}

.preview-content {
  position: relative;
  max-width: 90vw;
  max-height: 90vh;
}

.preview-content img {
  max-width: 100%;
  max-height: 90vh;
  border-radius: 8px;
}

.preview-close {
  position: absolute;
  top: -12px;
  right: -12px;
  width: 32px;
  height: 32px;
  background: rgba(239, 68, 68, 0.9);
  color: white;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  font-size: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Responsive */
@media (max-width: 1024px) {
  .image-gen-container {
    padding: 1rem;
  }
  
  .params-grid {
    grid-template-columns: 1fr;
  }
  
  .result-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  }
}

@media (max-width: 768px) {
  .result-grid {
    grid-template-columns: 1fr;
  }
  
  .history-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
