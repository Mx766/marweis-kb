<template>
  <el-result icon="warning" title="页面未找到" sub-title="请检查网址是否正确">
    <template #extra>
      <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
    </template>
  </el-result>
</template>
