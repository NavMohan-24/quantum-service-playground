package main

import "fmt"

type shape interface{
	getArea() float64
}

type square struct{
	sideLength float64
	base float64
}

type triangle struct{
	height float64
	base float64
}

func main(){
 
	s := square{sideLength: 5.0, base : 5.0}
	t := triangle{height: 5.0, base : 5.0 }

	printArea(s)
	printArea(t)
}

func (s square) getArea() float64{
	return s.sideLength * s.sideLength
}

func (t triangle) getArea() float64{
	return 0.5 * t.base * t.height
}

func printArea(sp shape) {
	fmt.Println("Area :", sp.getArea())
}