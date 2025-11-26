package main

import "os"
import "testing"

func TestNewDeck(t *testing.T){

	d := newDeck()
	if len(d) != 52{
		t.Errorf("Expected 52 cards in a deck, but got only %v", len(d))
	}

	if d[0] != "Ace of Spades"{
		t.Errorf("Expected Ace of Spades to be first card, but the first card is %v", d[0])
	}

	if d[len(d)-1] != "King of Clubs"{
		t.Errorf("Expected Ace of Spades to be first card, but the first card is %v", d[len(d)-1])
	}

}

func TestSaveFromDeckAndReadDeckFromFile(t *testing.T){

	os.Remove("_decktesting")

	deck := newDeck()
	deck.saveToFile("_decktesting")

	ldeck := readDeckFromFile("_decktesting")
	
	if len(ldeck) != 52{
		t.Errorf("Expected 52 cards in a deck, but got only %v", len(deck))
	}
	os.Remove("_decktesting")

}