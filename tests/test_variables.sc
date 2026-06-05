int global_val = 100;

int main() {
    int local_val = 50;
    int x = 0;
    int y = 5;

    printf("Global: %d, Local: %d\n", global_val, local_val);
    
    global_val += 10;
    local_val *= 2;
    printf("After edit: Global: %d, Local: %d\n", global_val, local_val);

    // Short circuit check
    if (x && (y = 10)) {
        printf("Fail\n");
    }
    printf("Short circuit AND: y is still %d\n", y);

    if (y || (x = 20)) {
        printf("Short circuit OR: x is still %d\n", x);
    }
    return 0;
}
