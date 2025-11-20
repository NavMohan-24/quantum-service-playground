package main

import (
	"fmt"
	"unsafe"
)

func main() {

	name := "bill" // defines the string header "name" (string type)
	name2 := name
	

	header := unsafe.StringData(name)
	header2 := unsafe.StringData(name2)
	fmt.Println("=== Heap Storage ===")
	fmt.Printf("String data pointer of name:   0x%x\n", header)
	fmt.Printf("String data pointer of name2:   0x%x\n", header2)


	namePointer := &name; // defines a pointer to the string header name (*string type)

	fmt.Println("=== In main ===")
    fmt.Printf("name is at address:        %p\n", &name)
    fmt.Printf("namePointer is at address: %p\n", &namePointer)
    fmt.Printf("namePointer contains:      %p\n", namePointer)
	// fmt.Println(namePointer)



	printPointer(namePointer)


	fmt.Printf("type of string header : %T\n" , name)
	fmt.Printf("type of string header pointer : %T\n" , namePointer)
}

func printPointer(namePointer *string){
    fmt.Println("\n=== In printPointer ===")
    fmt.Printf("parameter is at address:   %p\n", &namePointer)
    fmt.Printf("parameter contains:        %p\n", namePointer)
}

