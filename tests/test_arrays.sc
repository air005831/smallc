int main() {
    int data[5] = {10, 20, 30, 40, 50};
    char name[20] = "Hello";
    char dest[30];
    int cmp1;
    int cmp2;

    printf("data[2] = %d, data[4] = %d\n", data[2], data[4]);
    printf("name = %s, strlen = %d\n", name, strlen(name));
    
    // String functions: strcpy, strcat, strcmp
    strcpy(dest, name);
    printf("strcpy: dest = %s\n", dest);
    
    strcat(dest, " World");
    printf("strcat: dest = %s\n", dest);
    
    cmp1 = strcmp("abc", "abc");
    cmp2 = strcmp("abc", "abd");
    printf("strcmp same: %d, different: %d\n", cmp1, cmp2);
    
    return 0;
}
