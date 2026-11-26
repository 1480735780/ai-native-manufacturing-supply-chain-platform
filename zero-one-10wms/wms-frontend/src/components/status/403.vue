<!-- 403 页面 -->
<!-- 路由登记在 src/routers/index.ts 的 originRoutes（/forbidden）。本文件不在自动路由扫描目录 src/views 下，
     原先的 definePage() 不会被 unplugin-vue-router 转换，运行时直接抛 ReferenceError: definePage is not defined，
     表现为跳转后页面空白。2026-11-26 生产构建浏览器回归（cs/KH）实测确认。 -->

<template>
	<div class="contain">
		<div class="code">403</div>
		<div class="info">抱歉，你无权访问该页面</div>
	</div>
</template>

<style lang="css" scoped>
.contain {
	text-align: center;
	padding: 20%;
}
.code {
	font-size: xxx-large;
	font-weight: bold;
	color: #222222;
}
.info {
	font-weight: bold;
	color: dimgray;
}
</style>
