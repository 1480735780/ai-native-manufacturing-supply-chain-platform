<script lang="ts" setup>
import ReceiptList from "../components/receipt-list.vue";

definePage({
	meta: {
		menuType: "page",
		text: "收款管理",
		icon: "IconSetting",
	},
});
</script>

<template>
	<section class="receipt-root">
		<h2>收款管理</h2>
		<ReceiptList mode="received" />
	</section>
</template>

<style lang="scss" scoped>
.receipt-root {
	width: 100%;
}
</style>
