<template>
  <div class="oa-page">
    <div class="oa-head">
      <h2>OA 资料</h2>
      <p>按部门查看 OA 模块</p>
    </div>
    <div v-if="modules.length" class="oa-grid">
      <div v-for="m in modules" :key="m.id" class="oa-card">
        <div class="oa-card-head">{{ m.dept }}</div>
        <router-link
          v-for="ch in m.children"
          :key="ch.id"
          :to="'/category/' + ch.id"
          class="oa-item"
        >
          {{ ch.name }}
        </router-link>
        <router-link :to="'/category/' + m.id" class="oa-more">查看全部 →</router-link>
      </div>
    </div>
    <div v-else class="oa-empty">暂无 OA 模块</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { get } from '@/api/client'

const modules = ref<any[]>([])

onMounted(async () => {
  try {
    const cats: any[] = await get('/api/categories')
    modules.value = (cats || [])
      .filter((c: any) => /OA/i.test(c.name || ''))
      .map((c: any) => {
        const dept = (c.visible_departments && c.visible_departments[0]) || '公共'
        return { id: c.id, dept, name: c.name, children: c.children || [] }
      })
  } catch {}
})
</script>

<style scoped>
.oa-page { max-width: 1100px; margin: 0 auto; padding: 28px 20px; }
.oa-head { margin-bottom: 20px; }
.oa-head h2 { margin: 0 0 4px; font-size: 20px; color: #1f3a5f; }
.oa-head p { margin: 0; font-size: 13px; color: #888; }
.oa-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; }
.oa-card { border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px; background: #fff; }
.oa-card-head { font-size: 14px; font-weight: 600; color: #1f3a5f; padding-bottom: 8px; margin-bottom: 6px; border-bottom: 2px solid #eef1f5; }
.oa-item { display: block; padding: 7px 8px; font-size: 13px; color: #444; border-radius: 6px; text-decoration: none; }
.oa-item:hover { background: #f0f4f8; color: #1e50ae; }
.oa-more { display: inline-block; margin-top: 6px; padding: 5px 8px; font-size: 12px; color: #1e50ae; text-decoration: none; }
.oa-empty { padding: 60px 0; text-align: center; color: #bbb; font-size: 14px; }
</style>
