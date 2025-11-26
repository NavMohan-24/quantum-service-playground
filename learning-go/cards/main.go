package main

func main(){

	cards := newDeck()
	// cards.saveToFile("my_deck")
	cards.shuffle()
	cards.print()
}