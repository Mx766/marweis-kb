<template>
  <div class="md-preview" v-html="html"></div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps<{ source: string }>()

marked.setOptions({ gfm: true, breaks: true })

const html = computed(() => {
  const raw = props.source || ''
  return DOMPurify.sanitize(marked.parse(raw) as string)
})
</script>

<style scoped>
.md-preview {
  font-size: 14px;
  line-height: 1.75;
  color: #2b2f36;
  word-break: break-word;
}
.md-preview :deep(h1) { font-size: 22px; margin: 18px 0 12px; padding-bottom: 8px; border-bottom: 1px solid #e8eaed; }
.md-preview :deep(h2) { font-size: 19px; margin: 16px 0 10px; padding-bottom: 6px; border-bottom: 1px solid #f0f1f3; }
.md-preview :deep(h3) { font-size: 16px; margin: 14px 0 8px; }
.md-preview :deep(h4) { font-size: 14.5px; margin: 12px 0 6px; }
.md-preview :deep(p) { margin: 8px 0; }
.md-preview :deep(ul), .md-preview :deep(ol) { margin: 8px 0; padding-left: 24px; }
.md-preview :deep(li) { margin: 3px 0; }
.md-preview :deep(a) { color: var(--color-primary); text-decoration: none; }
.md-preview :deep(a:hover) { text-decoration: underline; }
.md-preview :deep(blockquote) {
  margin: 10px 0; padding: 8px 14px;
  border-left: 4px solid var(--color-primary);
  background: #f7f9fc; color: #555;
}
.md-preview :deep(code) {
  background: #f2f4f7; padding: 2px 5px; border-radius: 4px;
  font-size: 13px; font-family: Consolas, Menlo, monospace;
}
.md-preview :deep(pre) {
  background: #1e2430; color: #e6e8ee; padding: 14px 16px; border-radius: 8px;
  overflow-x: auto; margin: 10px 0;
}
.md-preview :deep(pre code) { background: transparent; padding: 0; color: inherit; }
.md-preview :deep(table) {
  border-collapse: collapse; width: 100%; margin: 12px 0;
  font-size: 13.5px;
}
.md-preview :deep(th), .md-preview :deep(td) {
  border: 1px solid #dfe3e8; padding: 7px 10px; text-align: left;
}
.md-preview :deep(th) { background: #f4f6f9; font-weight: 600; }
.md-preview :deep(tr:nth-child(even) td) { background: #fafbfc; }
.md-preview :deep(img) { max-width: 100%; border-radius: 6px; }
.md-preview :deep(hr) { border: none; border-top: 1px solid #e5e7eb; margin: 16px 0; }
</style>
