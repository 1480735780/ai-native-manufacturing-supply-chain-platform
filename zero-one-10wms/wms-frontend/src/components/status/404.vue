<!-- 404 页面 -->
<!-- 路由登记在 src/routers/index.ts 的 originRoutes（/:pathMatch(.*)*）。本文件不在自动路由扫描目录 src/views 下，
     原先的 definePage() 不会被 unplugin-vue-router 转换，运行时抛 ReferenceError: definePage is not defined。 -->

<template>
	<div class="contain">
		<div class="code">404</div>
		<div class="info">
			页面未找到<br />
			请检查你的路径
		</div>
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
