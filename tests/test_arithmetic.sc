int main() {
    printf("Precedence: 2 + 3 * 4 = %d\n", 2 + 3 * 4);
    printf("Parens: (2 + 3) * 4 = %d\n", (2 + 3) * 4);
    printf("Hex operations: 0xFF & 0x0F = %d\n", 0xFF & 0x0F);
    printf("Logical: 5 > 3 = %d, 5 < 3 = %d\n", 5 > 3, 5 < 3);
    return 0;
}
