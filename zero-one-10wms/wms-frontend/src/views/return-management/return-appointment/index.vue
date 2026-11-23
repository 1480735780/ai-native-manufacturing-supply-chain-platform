<script lang="ts" setup>
import NoticeOrderPage from "@/components/notice-order/NoticeOrderPage.vue";

definePage({
	meta: {
		menuType: "page",
		text: "退货预约",
		icon: "IconSetting",
	},
});
</script>

<template>
	<NoticeOrderPage title="退货预约" fixed-order-type-code="03" />
</template>
