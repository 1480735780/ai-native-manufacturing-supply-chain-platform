<script lang="ts" setup>
import GoodsReceivePage from "@/components/goods-receive/GoodsReceivePage.vue";

definePage({
	meta: {
		menuType: "page",
		text: "收货登记",
		icon: "IconSetting",
	},
});
</script>

<template>
	<GoodsReceivePage title="收货登记" />
</template>
