<script lang="ts" setup>
import { Platform } from "@element-plus/icons-vue";
definePage({
	meta: {
		menuType: "folder",
		text: "月台管理",
		icon: Platform,
	},
});
</script>

<template>
	<section class="yuetaiguanli-root">
		<RouterView></RouterView>
	</section>
</template>

<style lang="scss" scoped>
.yuetaiguanli-root {
}
</style>
