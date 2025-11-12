package main

import (
	"fmt"
	"os"
	"strings"
	"math/rand"
	"time"
)


type deck []string

// function to create a new deck
func newDeck() deck {

	cards := deck{}

	cardSuite := []string{"Spades", "Hearts", "Diamonds", "Clubs"}
	cardValues := []string{"Ace", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Jack", "Queen", "King"}

	for _, suite := range cardSuite {
		for _, vals := range cardValues {
			cards = append(cards, vals+" of "+suite)
		}
	}

	return cards
}

// Receiver function
func (d deck) print() {
	for index, card := range d {
		fmt.Println(index, card)
	}
}

func deal(d deck, handSize int) (deck, deck) {
	return d[:handSize], d[handSize:]
}

func (d deck) toString() string{
	return strings.Join(d, ",")
}

func (d deck) saveToFile(filename string) error{
	// WriteFile only takes bytes as input and 
	// file permissions also needs to be set
	// if the file is not existing.

	return os.WriteFile(filename, []byte(d.toString()), 0666)
}

func readDeckFromFile(filename string) deck{

	bs, err := os.ReadFile(filename)  

	if err != nil{

		fmt.Println("Error :", err)
		os.Exit(1)
		
	}

	s := strings.Split(string(bs),",")
	return deck(s)

}

func (d deck) shuffle() {

	// define a random number source passing current time as seed
	source := rand.NewSource(time.Now().UnixNano()) 
	// define a new random number generator
	r := rand.New(source) 

	for oldPos := range d{
		newPos := r.Intn(len(d)) // new position
		// swap the cards between old and new position
		d[oldPos], d[newPos] = d[newPos], d[oldPos]

	}

}