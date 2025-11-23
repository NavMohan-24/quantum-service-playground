package main

import (
	"fmt"
	"os"
	"gopkg.in/loremipsum.v1"
)

func main(){

	loremIpsumGenerator := loremipsum.New()
	sentence := loremIpsumGenerator.Sentence()

	// output 
	f, err := os.OpenFile("../testFile.txt", os.O_WRONLY|os.O_TRUNC, 0644) // opens the file with write only permission and truncate the existing data.
	if err != nil{
		fmt.Println("File path does not exist")
		os.Exit(1)
	}

	f.WriteString(sentence)

}