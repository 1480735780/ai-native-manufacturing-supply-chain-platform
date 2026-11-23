<script lang="ts" setup>
import NoticeOrderPage from "@/components/notice-order/NoticeOrderPage.vue";

definePage({
	meta: {
		menuType: "page",
		text: "入库通知单管理",
		icon: "IconSetting",
	},
});
</script>

<template>
	<NoticeOrderPage title="入库通知单" />
</template>
