<script lang="ts" setup>
import { Box } from "@element-plus/icons-vue";
definePage({
	meta: {
		menuType: "folder",
		text: "库内管理",
		icon: Box,
	},
});
</script>

<template>
	<section class="in-warehouse-root">
		<RouterView></RouterView>
	</section>
</template>

<style lang="scss" scoped>
.in-warehouse-root {
	width: 100%;
}
</style>
