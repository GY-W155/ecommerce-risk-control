<template>
  <el-container style="height: 100vh">
    <el-aside width="210px" style="background: #1f2d3d">
      <div class="logo">电商风控中心</div>
      <el-menu
        :default-active="$route.path"
        router
        background-color="#1f2d3d"
        text-color="#c0c4cc"
        active-text-color="#409eff"
      >
        <el-menu-item index="/dashboard">运营看板</el-menu-item>
        <el-menu-item index="/check">风险检查</el-menu-item>
        <el-menu-item index="/rules">规则管理</el-menu-item>
        <el-menu-item index="/cases">案件管理</el-menu-item>
        <el-menu-item index="/blacklists">黑名单</el-menu-item>
        <el-menu-item index="/profile">用户画像</el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <span class="header-title">{{ $route.meta?.title || '电商风控中心' }}</span>
        <el-badge value="风控系统" type="primary" style="margin-left: 8px" />
      </el-header>
      <el-main style="background: #f0f2f5; padding: 0">
        <div class="page">
          <router-view />
        </div>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
</script>

<style scoped>
.logo {
  color: #fff;
  font-size: 17px;
  font-weight: 700;
  text-align: center;
  line-height: 60px;
  letter-spacing: 2px;
}
.header {
  background: #fff;
  display: flex;
  align-items: center;
  border-bottom: 1px solid #e6e6e6;
}
.header-title {
  font-size: 18px;
  font-weight: 600;
}
</style>
