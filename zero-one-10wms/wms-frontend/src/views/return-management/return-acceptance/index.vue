<script lang="ts" setup>
import BatchAcceptPage from "@/components/batch-accept/BatchAcceptPage.vue";

definePage({
	meta: {
		menuType: "page",
		text: "退货验收",
		icon: "IconSetting",
	},
});
</script>

<template>
	<BatchAcceptPage title="退货验收" fixed-order-type-code="03" />
</template>
