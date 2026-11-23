import { computed } from "vue";
import { useUserStore } from "@/stores/user";
const READONLY_ROLES = ["cw", "\u8D22\u52A1", "KH", "\u5BA2\u6237", "\u53EA\u8BFB", "\u67E5\u770B", "readonly", "read_only", "viewer", "guest"];
function normalizeRole(role) {
  return String(role ?? "").trim().toLowerCase();
}
const READONLY_SET = new Set(READONLY_ROLES.map(normalizeRole));
function usePermission() {
  const userStore = useUserStore();
  const roles = computed(() => {
    const roles2 = userStore.getUser?.roles;
    return Array.isArray(roles2) ? roles2.map((item) => String(item)) : [];
  });
  const readOnly = computed(() => {
    if (roles.value.length === 0) return false;
    return roles.value.every((role) => READONLY_SET.has(normalizeRole(role)));
  });
  const canWrite = computed(() => !readOnly.value);
  return { roles, readOnly, canWrite };
}
export {
  READONLY_ROLES,
  usePermission
};
