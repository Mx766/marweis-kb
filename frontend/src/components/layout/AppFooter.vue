<template>
  <footer class="app-footer">
    <div class="footer-inner">
      <div class="footer-links">
        <router-link to="/" class="footer-logo">
          <span class="footer-logo-icon">M</span>
          <span>迈瑞生知识库</span>
        </router-link>
        <div class="footer-info">
          <p>©2026 北京迈瑞生医药科技有限公司 版权所有</p>
          <p>联系电话：400-853-5405 | 邮箱：bd@maris-reg.com</p>
          <p>地址：北京市东城区广渠门内大街90号新裕商务大厦B座10层</p>
        </div>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.app-footer {
  background: #2c3e50;
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
