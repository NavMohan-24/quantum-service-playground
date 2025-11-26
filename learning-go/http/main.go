package main

import (
	"fmt"
	"net/http"
	"os"
	"io"
)

func main(){
	resp, err := http.Get("http://google.com")

	if err != nil{
		fmt.Println("Error: ", err)
		os.Exit(1)
	}

	// fmt.Println(resp) // naive approach does not return response body

    // Getting the response body via reader interface

	bs := make([]byte, 99999) // empty byte slice with 99999 element capacity
	resp.Body.Read(bs) // slice is a reference type, modifying the copy will modify the original.
	fmt.Println(string(bs))

	/*
	response body is retrieved through reader interface
	implemented in http package. reader interface takes a 
	byte slice as an input.
	*/

	// Getting the response body via writer interface

	io.Copy(os.Stdout, resp.Body)
	/*
	Copy takes two values; one that implements the writer
	interface and the other that implements reader interface.

	`io.Copy` is copy data from a value that implements reader
	interface to value that implements writer interface.
		
	    os.Stdout --> Value of type *File --> File implements the Writer interface 
		resp.body --> Value of type *http.Response --> implememts Reader interface

	The writer interface could write the value to terminal or files etc.	
	*/


}