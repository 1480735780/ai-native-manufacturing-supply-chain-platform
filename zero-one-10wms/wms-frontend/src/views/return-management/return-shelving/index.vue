<script lang="ts" setup>
import GoodsReceivePage from "@/components/goods-receive/GoodsReceivePage.vue";

definePage({
	meta: {
		menuType: "page",
		text: "退货上架",
		icon: "IconSetting",
	},
});
</script>

<template>
	<GoodsReceivePage title="退货上架" fixed-order-type-code="03" />
</template>
