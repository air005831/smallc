int main() {
    int i;
    for (i = 1; i <= 4; i++) {
        printf("i = %d: ", i);
        switch (i) {
            case 1:
                printf("one\n");
                break;
            case 2:
                printf("two ");
                // fallthrough intentional
            case 3:
                printf("three\n");
                break;
            default:
                printf("other\n");
        }
    }
    return 0;
}
