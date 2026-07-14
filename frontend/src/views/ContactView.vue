<template>
  <div class="contact-page">
    <el-breadcrumb separator=">">
      <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
      <el-breadcrumb-item>通讯录</el-breadcrumb-item>
    </el-breadcrumb>

    <div class="contact-search">
      <el-input v-model="searchText" placeholder="搜索机构..." clearable size="large" style="max-width:480px" />
    </div>

    <div class="contact-grid" v-loading="loading">
      <div v-for="card in filteredContacts" :key="card.id" class="contact-card" @click="openDetail(card)">
        <div class="card-header">
          <span class="org-icon">🏛</span>
          <div class="org-info">
            <h3>{{ card.title }}</h3>
            <el-tag v-if="card.tags?.[0]" size="small">{{ card.tags[0] }}</el-tag>
          </div>
        </div>
        <div class="card-body">
          <p v-if="card.summary" class="org-summary">{{ card.summary }}</p>
          <p v-if="card.source" class="org-dept">📋 {{ card.source }}</p>
        </div>
        <div class="card-footer">
          <el-button v-if="card.source_url" size="small" type="primary" @click.stop="openWebsite(card.source_url)">
            访问官网
          </el-button>
          <el-button size="small" @click.stop="openDetail(card)">详情</el-button>
        </div>
      </div>

      <el-empty v-if="!loading && !filteredContacts.length" description="暂无通讯录数据" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { get } from '@/api/client'

const route = useRoute()
const router = useRouter()
const contacts = ref<any[]>([])
const loading = ref(false)
const searchText = ref('')

const filteredContacts = computed(() => {
  if (!searchText.value.trim()) return contacts.value
  const kw = searchText.value.trim().toLowerCase()
  return contacts.value.filter(c =>
    c.title.toLowerCase().includes(kw) ||
    (c.summary || '').toLowerCase().includes(kw) ||
    (c.source || '').toLowerCase().includes(kw)
  )
})

function openWebsite(url: string) {
  if (url) window.open(url, '_blank', 'noopener')
}

function openDetail(card: any) {
  if (card.source_url) {
    window.open(card.source_url, '_blank', 'noopener')
  } else {
    router.push(`/document/${card.id}`)
  }
}

onMounted(async () => {
  loading.value = true
  try {
    const catId = route.params.id as string
    const resp: any = await get('/api/documents', {
      category_id: catId,
      size: 100,
      sort: 'title',
      order: 'asc',
    })
    contacts.value = resp.items || []
  } catch {
    contacts.value = []
  }
  loading.value = false
})
</script>

<style scoped>
.contact-page { padding: var(--spacing-md) 0; }
.el-breadcrumb { margin-bottom: var(--spacing-md); }
.contact-search { margin-bottom: var(--spacing-lg); }

.contact-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.contact-card {
  background: #fff;
  border-radius: var(--radius-md);
  padding: 20px;
  box-shadow: var(--shadow-card);
  transition: all .2s;
  cursor: pointer;
}
.contact-card:hover {
  box-shadow: var(--shadow-hover);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}
.org-icon { font-size: 28px; flex-shrink: 0; }
.org-info { flex: 1; min-width: 0; }
.org-info h3 { font-size: 15px; margin: 0 0 4px; }
.card-body { margin-bottom: 12px; }
.org-summary {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.org-dept { font-size: 12px; color: var(--color-text-secondary); margin-top: 4px; }
.card-footer { display: flex; gap: 8px; }

@media (max-width: 768px) {
  .contact-grid { grid-template-columns: 1fr; }
}
</style>
