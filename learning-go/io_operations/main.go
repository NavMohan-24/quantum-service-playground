package main

import (
	"fmt"
	"io"
	"os"
)

func main(){

	// input
	file , errr := os.Open(os.Args[1])
	// data := make([]byte, 100)

	if errr != nil{
		fmt.Println("File path does not exist")
		os.Exit(1)
	}

	// file.Read(data)

	// fmt.Println(string(data))

	io.Copy(os.Stdout, file)


}
