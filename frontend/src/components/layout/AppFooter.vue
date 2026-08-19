<template>
  <footer class="app-footer">
    <div class="footer-inner">
      <div class="footer-links">
        <router-link to="/" class="footer-logo">
          <span class="footer-logo-icon">M</span>
          <span>企业知识库</span>
        </router-link>
        <div class="footer-info">
          <p>©{{ currentYear }} 企业知识库团队 版权所有</p>
          <p>技术支持：support@example.com</p>
          <p>地址：北京市东城区广渠门内大街90号新裕商务大厦B座10层</p>
        </div>
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">
const currentYear = new Date().getFullYear()
</script>

<style scoped>
.app-footer {
  background: #0f2c5c;
  color: #ecf0f1;
  padding: var(--spacing-xl) 0;
  margin-top: var(--spacing-2xl);
}
.footer-inner {
  max-width: 1300px;
  margin: 0 auto;
  padding: 0 var(--spacing-lg);
}
.footer-links {
  display: flex;
  gap: var(--spacing-2xl);
  align-items: flex-start;
}
.footer-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #ecf0f1 !important;
  font-size: 16px; font-weight: 600;
}
.footer-logo-icon {
  width: 44px; height: 44px;
  border-radius: 50%;
  background: var(--color-primary);
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; font-weight: 700;
  border: 2px solid rgba(255,255,255,.35);
}
.footer-info { font-size: 13px; line-height: 1.8; opacity: .75; }
.footer-info p { margin: 0; }
</style>
