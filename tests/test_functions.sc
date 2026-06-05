void print_sum(int a, int b) {
    printf("Sum: %d + %d = %d\n", a, b, a + b);
}

int multiply(int a, int b) {
    return a * b;
}

int main() {
    int prod = multiply(5, 6);
    print_sum(10, 20);
    printf("Product: %d\n", prod);
    return 0;
}
