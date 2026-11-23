<script lang="ts" setup>
import BatchAcceptPage from "@/components/batch-accept/BatchAcceptPage.vue";

definePage({
	meta: {
		menuType: "page",
		text: "批量收货",
		icon: "IconSetting",
	},
});
</script>

<template>
	<BatchAcceptPage title="待验收货物" />
</template>
