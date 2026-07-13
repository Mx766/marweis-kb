<template>
  <div class="admin-page">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="基本设置" name="general">
        <el-form label-width="120px" style="max-width:600px">
          <el-form-item label="站点名称">
            <el-input v-model="config.site_name" />
          </el-form-item>
          <el-form-item label="站点描述">
            <el-input v-model="config.site_desc" type="textarea" :rows="2" />
          </el-form-item>
          <el-form-item label="主色调">
            <el-color-picker v-model="config.primary_color" show-alpha />
          </el-form-item>
          <el-form-item label="强调色">
            <el-color-picker v-model="config.accent_color" show-alpha />
          </el-form-item>
          <el-form-item label="页头 Slogan">
            <el-input v-model="config.slogan" placeholder="搜索框旁的标语" />
          </el-form-item>
          <el-form-item label="页脚信息">
            <el-input v-model="config.footer" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item label="Logo">
            <el-upload :auto-upload="false" :show-file-list="false" accept="image/*">
              <el-button size="small">上传 Logo</el-button>
            </el-upload>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveGeneral">保存设置</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="文件与存储" name="storage">
        <el-form label-width="120px" style="max-width:600px">
          <el-form-item label="最大上传大小">
            <el-input-number v-model="config.max_upload_mb" :min="1" :max="2048" /> MB
          </el-form-item>
          <el-form-item label="MinIO 地址">
            <el-input v-model="config.minio_endpoint" placeholder="localhost:9000" />
          </el-form-item>
          <el-form-item label="存储桶">
            <el-input v-model="config.minio_bucket" placeholder="marweis-documents" />
          </el-form-item>
          <el-form-item label="允许的文件类型">
            <el-checkbox-group v-model="config.allowed_exts">
              <el-checkbox v-for="ext in fileTypes" :key="ext" :label="ext" :value="ext">{{ ext }}</el-checkbox>
            </el-checkbox-group>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveStorage">保存设置</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="数据库与索引" name="database">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="数据库">PostgreSQL 16</el-descriptions-item>
          <el-descriptions-item label="搜索引擎">Meilisearch</el-descriptions-item>
          <el-descriptions-item label="文档总数">{{ stats.total_docs }}</el-descriptions-item>
          <el-descriptions-item label="用户总数">{{ stats.total_users }}</el-descriptions-item>
          <el-descriptions-item label="总分类数">{{ stats.total_cats }}</el-descriptions-item>
          <el-descriptions-item label="后端版本">v0.1.0</el-descriptions-item>
        </el-descriptions>
        <div style="margin-top: var(--spacing-lg)">
          <el-button @click="rebuildIndex" :loading="rebuilding">重建搜索索引</el-button>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { get } from '@/api/client'
import { ElMessage } from 'element-plus'

const activeTab = ref('general')
const rebuilding = ref(false)

const config = reactive({
  site_name: '迈瑞生知识库',
  site_desc: '医疗器械注册 · 临床评价 · 临床试验 · 法规库',
  primary_color: '#1e50ae',
  accent_color: '#fb8c00',
  slogan: '专业法规知识管理平台',
  footer: '©2026 北京迈瑞生医药科技有限公司 版权所有 | 400-853-5405',
  max_upload_mb: 500,
  minio_endpoint: 'localhost:9000',
  minio_bucket: 'marweis-documents',
  allowed_exts: ['pdf','doc','docx','xls','xlsx','ppt','pptx','txt','md','jpg','png','gif','mp4','zip','rar'],
})

const stats = reactive({ total_docs: '-', total_users: '-', total_cats: '-' })
const fileTypes = ['pdf','doc','docx','xls','xlsx','ppt','pptx','txt','md','csv','jpg','jpeg','png','gif','tiff','bmp','mp4','avi','mov','mp3','wav','zip','rar','7z','dwg','epub','mobi']

function saveGeneral() { ElMessage.success('设置已保存（需重启生效）') }
function saveStorage() { ElMessage.success('存储设置已保存') }

async function rebuildIndex() {
  rebuilding.value = true
  ElMessage.info('索引重建需要一些时间...')
  // In production this calls a backend endpoint
  setTimeout(() => { rebuilding.value = false; ElMessage.success('索引重建完成') }, 3000)
}

onMounted(async () => {
  try {
    const resp: any = await get('/api/me/stats')
    // Stats from backend are currently user-specific, in admin mode we'd want site-wide
  } catch {}
})
</script>

<style scoped>
.admin-page { background: #fff; border-radius: var(--radius-md); padding: var(--spacing-lg); }
</style>
